import os
from main import getSegmentation, clear_logs, delete_files_in_folder
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_file, send_from_directory, make_response, session#, escape
from markupsafe import escape
from flask_login import login_required, current_user, login_user, logout_user, LoginManager
from werkzeug.utils import secure_filename
import logging
import zipfile
import json


# ----------------------------------------------------------------------------------------------
# FLASK

# Save images to the 'static' folder as Flask serves images from this directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/upload/') # /tmp cannot be used since we need access
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/download/') # /tmp cannot be used since we need access
ALLOWED_EXTENSIONS = {'gz', 'zip', '7z'}
LOGS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs/')

app = Flask(__name__, static_folder="static")

#Add reference fingerprint.
#Cookies travel with a signature that they claim to be legit.
#Legitimacy here means that the signature was issued by the owner of the cookie.
#Others cannot change this cookie as it needs the secret key.
#It's used as the key to encrypt the session - which can be stored in a cookie.
#Cookies should be encrypted if they contain potentially sensitive information.
app.secret_key = "secret key"

# Charge the whitelist of users
with open('whitelist.json', 'r') as f:
    whitelist = json.load(f)['users']

def check_credentials(username, password):
    for user in whitelist:
        if user['username'] == username and user['password'] == password:
            return True
    return False

#Define the upload folder to save images uploaded by the user. 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set Flask environment to development (to print console)
# os.system('export FLASK_APP=./a-eye_web/app.py')
os.environ['FLASK_APP'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app.py') # for flask run
os.environ['FLASK_DEBUG'] = 'True' # to print console

# Manage logs
logging.basicConfig(filename=f'{LOGS_FOLDER}app.log', level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(message)s')

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def zip_folder(source, destination):
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), os.path.join(source, '..')))

# ----------------------------------------------------------------------------------------------
# ROUTES

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html')
    return redirect(url_for('login'))
    

    
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        accept_terms = request.form.get('accept_terms')
        if not accept_terms:
            return "Vous devez accepter les conditions pour vous connecter.", 400
        if check_credentials(username, password):
            session['username'] = username
            return redirect(url_for('index'))
        else:
            return "Invalid credentials", 401
    return render_template('login.html')

@app.route('/informations')
def informations():
    if 'username' in session:
        return render_template('informations.html')
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    # remove the username from the session if it is there
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/getcookie')
def getcookie():
    name = request.cookies.get('userID')
    return '<h1>welcome ' + name + '</h1>'

@app.route('/segment')
def segment():
    # getSegmentation('/home/jaimebarranco/Desktop/test_inference/input')
    getSegmentation(UPLOAD_FOLDER, f'{DOWNLOAD_FOLDER}output/')
    # Zip folder to download
    zip_folder(f'{DOWNLOAD_FOLDER}output', f'{DOWNLOAD_FOLDER}output.zip')
    # Return the zip file as an attachment
    return send_file(f'{DOWNLOAD_FOLDER}output.zip', as_attachment=True)
    # return render_template('index.html', segmented=True)

@app.route('/', methods=['POST'])
def upload_files():
    if request.method == 'POST':
        if 'file' in request.files: # check if the post request has the file part
            files = request.files.getlist('file')
            if files != '': # empyt list
                for file in files:
                    if file and allowed_file(file.filename):
                        filename = secure_filename(file.filename) #Use this werkzeug method to secure filename. 
                        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(filepath)
                        return render_template('index.html', uploaded=True)
                    else:
                        flash('File not allowed')
                        return render_template('index.html', uploaded=False)
            else:
                flash('No file selected')
                return render_template('index.html', uploaded=False)
        else:
            flash('No file selected')
            return render_template('index.html', uploaded=False)


# ----------------------------------------------------------------------------------------------
# MAIN

if __name__ == '__main__':
    clear_logs(LOGS_FOLDER)
    delete_files_in_folder(UPLOAD_FOLDER)
    delete_files_in_folder(DOWNLOAD_FOLDER)
    app.run(host='0.0.0.0', port=5000, debug=True) # debug=True to development mode

# ----------------------------------------------------------------------------------------------
# UTILS

# Call flask from bash (other terminal)
# curl -X POST -H "Content-Type: application/json" -d '{"text":"predict"}' 0.0.0.0:5000/predict

# Finish open port
# netstat -nlp | grep 5000
# kill -9 441420

# Launch app.py and save console output
# /home/jaimebarranco/miniconda3/envs/a-eye/bin/python /mnt/sda1/Repos/a-eye/a-eye_web/app.py >> ./a-eye_web/logs/console.log 2>&1

# Complete command: args, logs
# /home/jaimebarranco/miniconda3/envs/a-eye/bin/python /mnt/sda1/Repos/a-eye/a-eye_web/app.py -i /home/jaimebarranco/Desktop/test_inference/input -o /home/jaimebarranco/Desktop/test_inference/output  >> ./a-eye_web/logs/console.log 2>&1

# Run docker with nvidia
# sudo docker run --rm --runtime=nvidia --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
# docker run --rm --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
# echo $SUDO_PWD | sudo -S -s docker run --rm --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
# LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1 docker run --rm --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi