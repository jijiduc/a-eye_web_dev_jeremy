import os
from main import getSegmentation, clear_logs, delete_files_in_folder, copy_folder
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_file, send_from_directory, make_response, session
from markupsafe import escape
from flask_login import login_required, current_user, login_user, logout_user, LoginManager
from werkzeug.utils import secure_filename
import logging
import zipfile
import json
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash


def zip_folder(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_path))
from models import db, User
from werkzeug.security import generate_password_hash, check_password_hash

# ----------------------------------------------------------------------------------------------
# FLASK

# Save images to the 'static' folder as Flask serves images from this directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/upload/') # /tmp cannot be used since we need access
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/download/') # /tmp cannot be used since we need access
ALLOWED_EXTENSIONS = {'gz', 'zip', '7z'}
LOGS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs/')

app = Flask(__name__, static_folder="static")

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "your_secret_key"  # Ensure you have a secret key for session management
db.init_app(app)

def create_tables():
    with app.app_context():
        db.create_all()

if not app._got_first_request:
    create_tables() # en appelant directement la fonction pour initialiser la BD

# ----------------------------------------------------------------------------------------------
# UTILS

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------------------------------------------------------------------------
# ROUTES

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['username'] = user.email
            return redirect(url_for('index'))
        else:
            flash('Incorrect password or email', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        password = generate_password_hash(request.form['password'])
        organization = request.form['organization']
        if organization == 'Other':
            organization = request.form['other_organization']
        job = request.form['job']
        
        # Verify if the email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email already exists.', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(email=email, first_name=first_name, last_name=last_name, password=password, organization=organization, job=job)
        db.session.add(new_user)
        db.session.commit()
        flash('Your account has been successfully created. An administrator must still validate your account before you can log in and use your account.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/users')
def users():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/')
def welcome():
    return render_template('welcomepage.html')

@app.route('/index')
def index():
    if 'username' in session:
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/informations')
def informations():
    if 'username' in session:
        return render_template('informations.html')
    return redirect(url_for('login'))


@app.route('/logout')
def logout():
    # remove the username from the session if it is there
    session.pop('username', None)
    return render_template('welcomepage.html')

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
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(UPLOAD_FOLDER, filename))
                return redirect(url_for('index'))
    return render_template('index.html')
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