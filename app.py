import os
from main import getSegmentation, clear_logs, delete_files_in_folder
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_file, send_from_directory
import logging
from werkzeug.utils import secure_filename
import zipfile

# ----------------------------------------------------------------------------------------------
# FLASK

# Save images to the 'static' folder as Flask serves images from this directory
# path to system folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/upload/')
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/download/')
# UPLOAD_FOLDER ='/tmp'
ALLOWED_EXTENSIONS = {'gz', 'zip'}
LOGS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs/')

app = Flask(__name__, static_folder="static")

#Add reference fingerprint.
#Cookies travel with a signature that they claim to be legit.
#Legitimacy here means that the signature was issued by the owner of the cookie.
#Others cannot change this cookie as it needs the secret key.
#It's used as the key to encrypt the session - which can be stored in a cookie.
#Cookies should be encrypted if they contain potentially sensitive information.
app.secret_key = "secret key"

#Define the upload folder to save images uploaded by the user. 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Set Flask environment to development (to print console)
# os.system('export FLASK_APP=./a-eye_web/app.py')
os.environ['FLASK_APP'] = './a-eye_web/app.py' # for flask run
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
def home():
    return render_template('base.html', uploaded=False, segmented=False)

@app.route('/segment')
def segment():
    # getSegmentation('/home/jaimebarranco/Desktop/test_inference/input')
    getSegmentation(UPLOAD_FOLDER, f'{DOWNLOAD_FOLDER}output/')
    # Zip folder to download
    zip_folder(f'{DOWNLOAD_FOLDER}output', f'{DOWNLOAD_FOLDER}output.zip')
    # Return the zip file as an attachment
    return send_file(f'{DOWNLOAD_FOLDER}output.zip', as_attachment=True)
    # return render_template('base.html', segmented=True)

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
                        return render_template('base.html', uploaded=True)
                    else:
                        flash('File not allowed')
                        return render_template('base.html', uploaded=False)
            else:
                flash('No file selected')
                return render_template('base.html', uploaded=False)
        else:
            flash('No file selected')
            return render_template('base.html', uploaded=False)


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