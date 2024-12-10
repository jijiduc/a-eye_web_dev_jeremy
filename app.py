import os
import secrets
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
from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client.errors import OAuthError, MismatchingStateError
from six.moves.urllib.parse import urlencode, quote_plus
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def zip_folder(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_path))

# ----------------------------------------------------------------------------------------------
# FLASK

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/upload/')
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/download/')
ALLOWED_EXTENSIONS = {'gz', 'zip', '7z'}
LOGS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs/')

app = Flask(__name__, static_folder="static")
app.config.from_object('config.Config')
app.secret_key = os.getenv('APP_SECRET_KEY', 'your_secret_key')

oauth = OAuth(app)
auth0 = oauth.register(
    'auth0',
    client_id=app.config['AUTH0_CLIENT_ID'],
    client_secret=app.config['AUTH0_CLIENT_SECRET'],
    api_base_url=f"https://{app.config['AUTH0_DOMAIN']}",
    access_token_url=f"https://{app.config['AUTH0_DOMAIN']}/oauth/token",
    authorize_url=f"https://{app.config['AUTH0_DOMAIN']}/authorize",
    client_kwargs={
        'scope': 'openid profile email',
    },
    server_metadata_url=f"https://{app.config['AUTH0_DOMAIN']}/.well-known/openid-configuration"
)



# Load whitelist
with open('whitelist.json', 'r') as f:
    whitelist = json.load(f)['whitelist']

# ----------------------------------------------------------------------------------------------
# UTILS

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ----------------------------------------------------------------------------------------------
# ROUTES

@app.route("/")
def welcome():
    return render_template("welcomepage.html")

@app.route("/callback", methods=["GET", "POST"])
def callback():
    try:
        token = oauth.auth0.authorize_access_token()
        state = session.pop('state', None)
        if request.args.get('state') != state:
            raise MismatchingStateError()
        nonce = session.pop('nonce', None)
        userinfo = oauth.auth0.parse_id_token(token, nonce=nonce)
        
        # Vérifier si l'email est vérifié
        if not userinfo.get('email_verified'):
            return redirect(url_for('verify_email'))
        
        session["user"] = userinfo
        return redirect(url_for('segmentationtool'))
    except OAuthError as error:
        flash("Erreur d'authentification : " + error.description)
        return redirect(url_for('welcome'))

@app.route("/verify_email")
def verify_email():
    return render_template("verify_email.html")

@app.route("/login")
def login():
    nonce = secrets.token_urlsafe()
    state = secrets.token_urlsafe()
    session['nonce'] = nonce
    session['state'] = state
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("callback", _external=True),
        nonce=nonce,
        state=state
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + os.getenv("AUTH0_DOMAIN") + "/v2/logout?" + urlencode(
            {
                "returnTo": url_for("welcome", _external=True),
                "client_id": os.getenv("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )
@app.route("/services")
def services():
    return render_template("services.html")

@app.route('/users')
def users():
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route('/segmentationtool')
def segmentationtool():
    if 'user' in session:
        return render_template('segmentationtool.html')
    return redirect(url_for('login'))

@app.route('/informations')
def informations():
    return render_template('informations.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'file' in request.files: # check if the post request has the file part
        files = request.files.getlist('file')
        if files: # non-empty list
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(UPLOAD_FOLDER, filename))
            return redirect(url_for('segmentationtool'))
    return render_template('segmentationtool.html')

# ----------------------------------------------------------------------------------------------
# MAIN

if __name__ == '__main__':
    clear_logs(LOGS_FOLDER)
    delete_files_in_folder(UPLOAD_FOLDER)
    delete_files_in_folder(DOWNLOAD_FOLDER)
    app.run(host='0.0.0.0', port=5000, debug=True)