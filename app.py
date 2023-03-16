import os
from main import getSegmentation, clear_app_logs, clear_console_logs
from flask import Flask, request, jsonify, render_template, request, redirect, url_for, flash
import logging
from werkzeug.utils import secure_filename

# ----------------------------------------------------------------------------------------------
# FLASK

#Save images to the 'static' folder as Flask serves images from this directory
# UPLOAD_FOLDER = os.path('./a-eye_web/static/images/')
# path to system folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/images/')
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


# ----------------------------------------------------------------------------------------------
# ROUTES

@app.route('/')
def home():
    return render_template('base.html', done=False)

@app.route('/predict')
def predict():
    getSegmentation()
    return render_template('base.html', done=True)

#Add Post method to the decorator to allow for form submission. 
@app.route('/', methods=['POST'])
def submit_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No file selected for uploading')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename) #Use this werkzeug method to secure filename. 
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            result = getSegmentation(filepath)
            flash(result)
            # full_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # flash(full_filepath)
            return render_template('base.html', done=True)
            # return redirect(url_for('home'))


# ----------------------------------------------------------------------------------------------
# MAIN

if __name__ == '__main__':
    clear_app_logs(LOGS_FOLDER)
    clear_console_logs(LOGS_FOLDER)
    app.run(host='0.0.0.0', port=5000, debug=True) # debug=True to development mode

# ----------------------------------------------------------------------------------------------
# UTILS

# Call flask from bash (other terminal)
# curl -X POST -H "Content-Type: application/json" -d '{"text":"predict"}' 0.0.0.0:5000/predict

# Finish open port
# netstat -nlp | grep 5000
# kill -9 441420

# Launch app.py and save console output
# /home/jaimebarranco/miniconda3/envs/a-eye/bin/python /mnt/sda1/Repos/a-eye/a-eye_web/app.py >> ./a-eye_web/console.log 2>&1

# Complete command: args, logs
# /home/jaimebarranco/miniconda3/envs/a-eye/bin/python /mnt/sda1/Repos/a-eye/a-eye_web/app.py -i /home/jaimebarranco/Desktop/test_inference/input -o /home/jaimebarranco/Desktop/test_inference/output  >> ./a-eye_web/logs/console.log 2>&1

# Run docker with nvidia
# sudo docker run --rm --runtime=nvidia --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
# docker run --rm --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
# echo $SUDO_PWD | sudo -S -s docker run --rm --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi
# LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libnvidia-ml.so.1 docker run --rm --gpus all nvidia/cuda:11.6.2-base-ubuntu20.04 nvidia-smi


