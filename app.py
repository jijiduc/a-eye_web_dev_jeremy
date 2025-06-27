import os
import secrets
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_file, session
import requests
import logging
from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client.errors import OAuthError, MismatchingStateError
from urllib.parse import urlencode, quote_plus
from dotenv import load_dotenv
import pandas as pd
import plotly.express as px
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
import threading

from main import getSegmentation

from utils import (
    delete_files_in_folder,
    delete_subfolders,
    clear_logs,
    allowed_file,
    copy_segmentation_data,
    get_country_from_ip,
    convert_country_to_iso3,
    requires_auth,
    zip_folder
)

from config import (
    LOGS_FOLDER,
    UPLOAD_FOLDER, 
    DOWNLOAD_FOLDER,
    OUTPUT_ZIP, 
)


# Load environment variables from .env file
load_dotenv()

# Manage logs
logging.basicConfig(filename=f'{LOGS_FOLDER}/app.log', level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(name)s %(message)s')

# Initialize global variable
cases_processed = 0
high_scale_nb_users = 100  # Set the maximum number of users for the color scale


# ----------------------------------------------------------------------------------------------
# FLASK

app = Flask(__name__, static_folder="static")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

app.config.from_object('config.Config')
app.secret_key = os.getenv('APP_SECRET_KEY', 'ALongRandomlyGeneratedString')
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # for https
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

mail = Mail(app)

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


# ----------------------------------------------------------------------------------------------
# DEFS

def get_management_api_token():
    url = f'https://{app.config["AUTH0_DOMAIN"]}/oauth/token'
    payload = {
        'client_id': app.config['AUTH0_CLIENT_ID'],
        'client_secret': app.config['AUTH0_CLIENT_SECRET'],
        'audience': f'https://{app.config["AUTH0_DOMAIN"]}/api/v2/',
        'grant_type': 'client_credentials'
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()['access_token']

def get_user_data():
    auth0_domain = app.config['AUTH0_DOMAIN']
    access_token = get_management_api_token()
    headers = {'Authorization': f'Bearer {access_token}'}

    # Include fields you want explicitly
    params = {
        'fields': 'email,last_ip',
        'include_fields': 'true',
        'per_page': 100,
        'page': 0
    }

    all_users = []
    while True:
        response = requests.get(
            f'https://{auth0_domain}/api/v2/users',
            headers=headers,
            params=params
        )
        response.raise_for_status()
        page_users = response.json()
        if not page_users:
            break
        all_users.extend(page_users)
        params['page'] += 1

    return all_users


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
        return redirect(url_for('segmentation'))
    except OAuthError as error:
        flash("Authentication failed: " + error.description)
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
        "https://" + app.config['AUTH0_DOMAIN'] + "/v2/logout?" + urlencode(
            {
                "returnTo": url_for("welcome", _external=True),
                "client_id": app.config['AUTH0_CLIENT_ID'],
            },
            quote_via=quote_plus,
        )
    )

@app.route('/users')
def users():
    users_data = get_user_data()
    total_users = len(users_data)
    
    # Calculate the number of institutions
    domains = set()
    for user in users_data:
        print("User: ", user)
        email = user.get('email')
        if email:
            domain = email.split('@')[-1]
            domains.add(domain)
    total_institutions = len(domains)
    print(f"Total Users: {total_users}, Total Institutions: {total_institutions}")
    
    # Get country data from user IPs
    country_counts = {}
    for user in users_data:
        if isinstance(user, dict):
            ip = user.get('last_ip')
            if ip:
                country = get_country_from_ip(ip)
                if country:
                    country_iso3 = convert_country_to_iso3(country)
                    if country_iso3:
                        if country_iso3 in country_counts:
                            country_counts[country_iso3] += 1
                        else:
                            country_counts[country_iso3] = 1
    
    # Create a DataFrame for the country data
    df = pd.DataFrame(list(country_counts.items()), columns=['Country', 'Count'])
    print(df)  # Debugging: Print DataFrame
    
    # Generate the choropleth map
    fig = px.choropleth(df, locations="Country", locationmode='ISO-3', color="Count",
                        color_continuous_scale="Greens", range_color=(0, high_scale_nb_users),
                        width=1200, height=675)  # Set the width and height of the figure
    
    fig.update_layout(
        margin={"r":0,"t":0,"l":0,"b":0},
        geo=dict(
            showframe=False,
            showcoastlines=False,
            projection_type='equirectangular',
            # Center the map
            lataxis=dict(range=[-90, 90]),  # Adjust latitude range to exclude Antarctica
            lonaxis=dict(range=[-180, 180])  # Adjust longitude range to show the whole world
        )
    )
    
    fig.update_layout(
        dragmode=False,
        geo=dict(
            showframe=False,
            showcoastlines=False,
            projection_type='equirectangular',
            center=dict(lat=0, lon=0)  # Center the map
        ),
        coloraxis_showscale=False  # Remove the color scale
    )
    
    map_html = fig.to_html(full_html=False)
    
    return render_template('users.html', total_users=total_users, cases_processed=cases_processed, total_institutions=total_institutions, map_html=map_html)


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/segmentation")
def segmentation():
    if 'user' in session:
        return render_template('segmentation.html')
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_file():
         
    if 'files[]' not in request.files:
        return jsonify({'message': 'No file found', 'status': 'error'}), 400
    
    files = request.files.getlist('files[]')
    uploaded_files = []
    rejected_files = []
    
    clear_logs(LOGS_FOLDER)  # Clear previous logs
    delete_files_in_folder("/app/nnUNet/nnUNet_inference")  # Clear output.zip
    delete_files_in_folder("/app/nnUNet/nnUNet_inference/input")  # Clear previous inference files
    delete_subfolders("/app/nnUNet/nnUNet_inference/input")  # Clear previous uploaded files
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)  # Use this werkzeug method to secure filename.
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_files.append(filename)
        else:
            rejected_files.append(file.filename)
    
    if uploaded_files:
        message = f"Uploaded: {', '.join(uploaded_files)}"
        if rejected_files:
            message += f" | Rejected: {', '.join(rejected_files)}"
        return jsonify({'message': message, 'status': 'success'}), 200
    else:
        return jsonify({'message': 'No valid files uploaded', 'status': 'error'}), 400

@app.route('/segment', methods=['POST'])
def segment():
    # Run segmentation function
    getSegmentation(UPLOAD_FOLDER, DOWNLOAD_FOLDER)

    # Zip folder for download
    zip_folder(DOWNLOAD_FOLDER, OUTPUT_ZIP)
    
    # Get user email from session or token
    user_email = session.get("user", {}).get("email", "unknown_user")
    
    # Start background thread to copy files (only if output exists)
    has_output = (
        os.path.exists(DOWNLOAD_FOLDER) and
        any(fname.endswith(".nii.gz") for fname in os.listdir(DOWNLOAD_FOLDER))
    )

    if has_output:
        threading.Thread(
            target=copy_segmentation_data,
            args=(user_email, "/app/nnUNet/nnUNet_inference/input", DOWNLOAD_FOLDER)
        ).start()
    else:
        print("[A-eye] Segmentation failed or no .nii.gz output found. Data not copied!")

    return jsonify({"message": "Segmentation completed", "download_url": "/download"}), 200

@app.route('/profile')
@requires_auth  # Ensure only logged-in users can view this
def profile():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    return render_template("profile.html", user=user)

@app.route('/download', methods=['GET'])
def download_files():
    if os.path.exists(OUTPUT_ZIP):
        return send_file(OUTPUT_ZIP, as_attachment=True)
    return "File not found", 404

def send_email(to):
    msg = Message('Segmentation Task Completed', recipients=[to])
    msg.body = 'Your segmentation task has been completed successfully. You can now download the results from the AEye platform.'
    mail.send(msg)


# ----------------------------------------------------------------------------------------------
# MAIN

if __name__ == '__main__':
    clear_logs(LOGS_FOLDER)  # Clear previous logs
    delete_files_in_folder("/app/nnUNet/nnUNet_inference")  # Clear output.zip
    delete_files_in_folder("/app/nnUNet/nnUNet_inference/input")  # Clear previous inference files
    delete_subfolders("/app/nnUNet/nnUNet_inference/input")  # Clear previous uploaded files
    app.run(host='0.0.0.0', port=5000, debug=True)


# ----------------------------------------------------------------------------------------------
# MISC

# Finish open port
# lsof -i :5000
# kill -9 <process_id>
