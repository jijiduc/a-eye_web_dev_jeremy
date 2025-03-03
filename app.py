import os
import secrets
from main import getSegmentation, clear_logs, delete_files_in_folder, copy_folder
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash, send_file, send_from_directory, make_response, session
import logging
import zipfile
import json
from authlib.integrations.flask_client import OAuth
from authlib.integrations.base_client.errors import OAuthError, MismatchingStateError
from urllib.parse import urlencode, quote_plus
from dotenv import load_dotenv
import requests
import pandas as pd
import plotly.express as px
import pycountry
import subprocess
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename


UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/upload/')
DOWNLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static/download/')
ALLOWED_EXTENSIONS = {'gz', 'zip', '7z'}
OUTPUT_ZIP = os.path.join(DOWNLOAD_FOLDER, "output.zip")
LOGS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs/')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def zip_folder(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_path))

def get_user_data():
    auth0_domain = os.getenv('AUTH0_DOMAIN')
    access_token = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InlhQmkzVUVlMDI5UDFsWVB4bFczLSJ9.eyJpc3MiOiJodHRwczovL2Rldi1lZm83aTV3d3FzbWZzcXZ0LmV1LmF1dGgwLmNvbS8iLCJzdWIiOiJXVjJSWUk3akFwcDN3cmEyb3hwTWMwS1pmOFoxbDZXUUBjbGllbnRzIiwiYXVkIjoiaHR0cHM6Ly9kZXYtZWZvN2k1d3dxc21mc3F2dC5ldS5hdXRoMC5jb20vYXBpL3YyLyIsImlhdCI6MTczNzA3MjU5MywiZXhwIjoxNzM5NjY0NTkzLCJzY29wZSI6InJlYWQ6Y2xpZW50X2dyYW50cyBjcmVhdGU6Y2xpZW50X2dyYW50cyBkZWxldGU6Y2xpZW50X2dyYW50cyB1cGRhdGU6Y2xpZW50X2dyYW50cyByZWFkOnVzZXJzIHVwZGF0ZTp1c2VycyBkZWxldGU6dXNlcnMgY3JlYXRlOnVzZXJzIHJlYWQ6dXNlcnNfYXBwX21ldGFkYXRhIHVwZGF0ZTp1c2Vyc19hcHBfbWV0YWRhdGEgZGVsZXRlOnVzZXJzX2FwcF9tZXRhZGF0YSBjcmVhdGU6dXNlcnNfYXBwX21ldGFkYXRhIHJlYWQ6dXNlcl9jdXN0b21fYmxvY2tzIGNyZWF0ZTp1c2VyX2N1c3RvbV9ibG9ja3MgZGVsZXRlOnVzZXJfY3VzdG9tX2Jsb2NrcyBjcmVhdGU6dXNlcl90aWNrZXRzIHJlYWQ6Y2xpZW50cyB1cGRhdGU6Y2xpZW50cyBkZWxldGU6Y2xpZW50cyBjcmVhdGU6Y2xpZW50cyByZWFkOmNsaWVudF9rZXlzIHVwZGF0ZTpjbGllbnRfa2V5cyBkZWxldGU6Y2xpZW50X2tleXMgY3JlYXRlOmNsaWVudF9rZXlzIHJlYWQ6Y29ubmVjdGlvbnMgdXBkYXRlOmNvbm5lY3Rpb25zIGRlbGV0ZTpjb25uZWN0aW9ucyBjcmVhdGU6Y29ubmVjdGlvbnMgcmVhZDpyZXNvdXJjZV9zZXJ2ZXJzIHVwZGF0ZTpyZXNvdXJjZV9zZXJ2ZXJzIGRlbGV0ZTpyZXNvdXJjZV9zZXJ2ZXJzIGNyZWF0ZTpyZXNvdXJjZV9zZXJ2ZXJzIHJlYWQ6ZGV2aWNlX2NyZWRlbnRpYWxzIHVwZGF0ZTpkZXZpY2VfY3JlZGVudGlhbHMgZGVsZXRlOmRldmljZV9jcmVkZW50aWFscyBjcmVhdGU6ZGV2aWNlX2NyZWRlbnRpYWxzIHJlYWQ6cnVsZXMgdXBkYXRlOnJ1bGVzIGRlbGV0ZTpydWxlcyBjcmVhdGU6cnVsZXMgcmVhZDpydWxlc19jb25maWdzIHVwZGF0ZTpydWxlc19jb25maWdzIGRlbGV0ZTpydWxlc19jb25maWdzIHJlYWQ6aG9va3MgdXBkYXRlOmhvb2tzIGRlbGV0ZTpob29rcyBjcmVhdGU6aG9va3MgcmVhZDphY3Rpb25zIHVwZGF0ZTphY3Rpb25zIGRlbGV0ZTphY3Rpb25zIGNyZWF0ZTphY3Rpb25zIHJlYWQ6ZW1haWxfcHJvdmlkZXIgdXBkYXRlOmVtYWlsX3Byb3ZpZGVyIGRlbGV0ZTplbWFpbF9wcm92aWRlciBjcmVhdGU6ZW1haWxfcHJvdmlkZXIgYmxhY2tsaXN0OnRva2VucyByZWFkOnN0YXRzIHJlYWQ6aW5zaWdodHMgcmVhZDp0ZW5hbnRfc2V0dGluZ3MgdXBkYXRlOnRlbmFudF9zZXR0aW5ncyByZWFkOmxvZ3MgcmVhZDpsb2dzX3VzZXJzIHJlYWQ6c2hpZWxkcyBjcmVhdGU6c2hpZWxkcyB1cGRhdGU6c2hpZWxkcyBkZWxldGU6c2hpZWxkcyByZWFkOmFub21hbHlfYmxvY2tzIGRlbGV0ZTphbm9tYWx5X2Jsb2NrcyB1cGRhdGU6dHJpZ2dlcnMgcmVhZDp0cmlnZ2VycyByZWFkOmdyYW50cyBkZWxldGU6Z3JhbnRzIHJlYWQ6Z3VhcmRpYW5fZmFjdG9ycyB1cGRhdGU6Z3VhcmRpYW5fZmFjdG9ycyByZWFkOmd1YXJkaWFuX2Vucm9sbG1lbnRzIGRlbGV0ZTpndWFyZGlhbl9lbnJvbGxtZW50cyBjcmVhdGU6Z3VhcmRpYW5fZW5yb2xsbWVudF90aWNrZXRzIHJlYWQ6dXNlcl9pZHBfdG9rZW5zIGNyZWF0ZTpwYXNzd29yZHNfY2hlY2tpbmdfam9iIGRlbGV0ZTpwYXNzd29yZHNfY2hlY2tpbmdfam9iIHJlYWQ6Y3VzdG9tX2RvbWFpbnMgZGVsZXRlOmN1c3RvbV9kb21haW5zIGNyZWF0ZTpjdXN0b21fZG9tYWlucyB1cGRhdGU6Y3VzdG9tX2RvbWFpbnMgcmVhZDplbWFpbF90ZW1wbGF0ZXMgY3JlYXRlOmVtYWlsX3RlbXBsYXRlcyB1cGRhdGU6ZW1haWxfdGVtcGxhdGVzIHJlYWQ6bWZhX3BvbGljaWVzIHVwZGF0ZTptZmFfcG9saWNpZXMgcmVhZDpyb2xlcyBjcmVhdGU6cm9sZXMgZGVsZXRlOnJvbGVzIHVwZGF0ZTpyb2xlcyByZWFkOnByb21wdHMgdXBkYXRlOnByb21wdHMgcmVhZDpicmFuZGluZyB1cGRhdGU6YnJhbmRpbmcgZGVsZXRlOmJyYW5kaW5nIHJlYWQ6bG9nX3N0cmVhbXMgY3JlYXRlOmxvZ19zdHJlYW1zIGRlbGV0ZTpsb2dfc3RyZWFtcyB1cGRhdGU6bG9nX3N0cmVhbXMgY3JlYXRlOnNpZ25pbmdfa2V5cyByZWFkOnNpZ25pbmdfa2V5cyB1cGRhdGU6c2lnbmluZ19rZXlzIHJlYWQ6bGltaXRzIHVwZGF0ZTpsaW1pdHMgY3JlYXRlOnJvbGVfbWVtYmVycyByZWFkOnJvbGVfbWVtYmVycyBkZWxldGU6cm9sZV9tZW1iZXJzIHJlYWQ6ZW50aXRsZW1lbnRzIHJlYWQ6YXR0YWNrX3Byb3RlY3Rpb24gdXBkYXRlOmF0dGFja19wcm90ZWN0aW9uIHJlYWQ6b3JnYW5pemF0aW9uc19zdW1tYXJ5IGNyZWF0ZTphdXRoZW50aWNhdGlvbl9tZXRob2RzIHJlYWQ6YXV0aGVudGljYXRpb25fbWV0aG9kcyB1cGRhdGU6YXV0aGVudGljYXRpb25fbWV0aG9kcyBkZWxldGU6YXV0aGVudGljYXRpb25fbWV0aG9kcyByZWFkOm9yZ2FuaXphdGlvbnMgdXBkYXRlOm9yZ2FuaXphdGlvbnMgY3JlYXRlOm9yZ2FuaXphdGlvbnMgZGVsZXRlOm9yZ2FuaXphdGlvbnMgY3JlYXRlOm9yZ2FuaXphdGlvbl9tZW1iZXJzIHJlYWQ6b3JnYW5pemF0aW9uX21lbWJlcnMgZGVsZXRlOm9yZ2FuaXphdGlvbl9tZW1iZXJzIGNyZWF0ZTpvcmdhbml6YXRpb25fY29ubmVjdGlvbnMgcmVhZDpvcmdhbml6YXRpb25fY29ubmVjdGlvbnMgdXBkYXRlOm9yZ2FuaXphdGlvbl9jb25uZWN0aW9ucyBkZWxldGU6b3JnYW5pemF0aW9uX2Nvbm5lY3Rpb25zIGNyZWF0ZTpvcmdhbml6YXRpb25fbWVtYmVyX3JvbGVzIHJlYWQ6b3JnYW5pemF0aW9uX21lbWJlcl9yb2xlcyBkZWxldGU6b3JnYW5pemF0aW9uX21lbWJlcl9yb2xlcyBjcmVhdGU6b3JnYW5pemF0aW9uX2ludml0YXRpb25zIHJlYWQ6b3JnYW5pemF0aW9uX2ludml0YXRpb25zIGRlbGV0ZTpvcmdhbml6YXRpb25faW52aXRhdGlvbnMgcmVhZDpzY2ltX2NvbmZpZyBjcmVhdGU6c2NpbV9jb25maWcgdXBkYXRlOnNjaW1fY29uZmlnIGRlbGV0ZTpzY2ltX2NvbmZpZyBjcmVhdGU6c2NpbV90b2tlbiByZWFkOnNjaW1fdG9rZW4gZGVsZXRlOnNjaW1fdG9rZW4gZGVsZXRlOnBob25lX3Byb3ZpZGVycyBjcmVhdGU6cGhvbmVfcHJvdmlkZXJzIHJlYWQ6cGhvbmVfcHJvdmlkZXJzIHVwZGF0ZTpwaG9uZV9wcm92aWRlcnMgZGVsZXRlOnBob25lX3RlbXBsYXRlcyBjcmVhdGU6cGhvbmVfdGVtcGxhdGVzIHJlYWQ6cGhvbmVfdGVtcGxhdGVzIHVwZGF0ZTpwaG9uZV90ZW1wbGF0ZXMgY3JlYXRlOmVuY3J5cHRpb25fa2V5cyByZWFkOmVuY3J5cHRpb25fa2V5cyB1cGRhdGU6ZW5jcnlwdGlvbl9rZXlzIGRlbGV0ZTplbmNyeXB0aW9uX2tleXMgcmVhZDpzZXNzaW9ucyBkZWxldGU6c2Vzc2lvbnMgcmVhZDpyZWZyZXNoX3Rva2VucyBkZWxldGU6cmVmcmVzaF90b2tlbnMgY3JlYXRlOnNlbGZfc2VydmljZV9wcm9maWxlcyByZWFkOnNlbGZfc2VydmljZV9wcm9maWxlcyB1cGRhdGU6c2VsZl9zZXJ2aWNlX3Byb2ZpbGVzIGRlbGV0ZTpzZWxmX3NlcnZpY2VfcHJvZmlsZXMgY3JlYXRlOnNzb19hY2Nlc3NfdGlja2V0cyBkZWxldGU6c3NvX2FjY2Vzc190aWNrZXRzIHJlYWQ6Zm9ybXMgdXBkYXRlOmZvcm1zIGRlbGV0ZTpmb3JtcyBjcmVhdGU6Zm9ybXMgcmVhZDpmbG93cyB1cGRhdGU6Zmxvd3MgZGVsZXRlOmZsb3dzIGNyZWF0ZTpmbG93cyByZWFkOmZsb3dzX3ZhdWx0IHJlYWQ6Zmxvd3NfdmF1bHRfY29ubmVjdGlvbnMgdXBkYXRlOmZsb3dzX3ZhdWx0X2Nvbm5lY3Rpb25zIGRlbGV0ZTpmbG93c192YXVsdF9jb25uZWN0aW9ucyBjcmVhdGU6Zmxvd3NfdmF1bHRfY29ubmVjdGlvbnMgcmVhZDpmbG93c19leGVjdXRpb25zIGRlbGV0ZTpmbG93c19leGVjdXRpb25zIHJlYWQ6Y29ubmVjdGlvbnNfb3B0aW9ucyB1cGRhdGU6Y29ubmVjdGlvbnNfb3B0aW9ucyByZWFkOnNlbGZfc2VydmljZV9wcm9maWxlX2N1c3RvbV90ZXh0cyB1cGRhdGU6c2VsZl9zZXJ2aWNlX3Byb2ZpbGVfY3VzdG9tX3RleHRzIHJlYWQ6Y2xpZW50X2NyZWRlbnRpYWxzIGNyZWF0ZTpjbGllbnRfY3JlZGVudGlhbHMgdXBkYXRlOmNsaWVudF9jcmVkZW50aWFscyBkZWxldGU6Y2xpZW50X2NyZWRlbnRpYWxzIHJlYWQ6b3JnYW5pemF0aW9uX2NsaWVudF9ncmFudHMgY3JlYXRlOm9yZ2FuaXphdGlvbl9jbGllbnRfZ3JhbnRzIGRlbGV0ZTpvcmdhbml6YXRpb25fY2xpZW50X2dyYW50cyIsImd0eSI6ImNsaWVudC1jcmVkZW50aWFscyIsImF6cCI6IldWMlJZSTdqQXBwM3dyYTJveHBNYzBLWmY4WjFsNldRIn0.rE0dkGzZz4cLFSk-IQGfEhfMBmrFRpQoF1mzCNEot5vKvAHKiOmcTESh3Q-gmZg2MznIR-3OMt20pObdmhAwynioh7qjwyGzgC76nAPcBdCaGr-wFqhPnEFgpQ_FJbhlhctNWRd_jDmXJN9rLC2yCZCXPCa4LqzOrUVJX9LeEj8vvS2pnGTly_NEzDJYsW2wCP8sC8EXAqy5T_bGMGjjPfBiARTpRyUCZvWDvTMM9IDSyekFAvsiAIGqtbaLv8ZfKgSjpw3i1fTcNHZRPBoV6OUvBJ2EinsPjEKigvsV5dD96uPWRw_WqRyKB7kTwaYh3b_uGBrp61JW1HyP31CFZQ'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f'https://{auth0_domain}/api/v2/users', headers=headers)
    response.raise_for_status()  # Raise an exception for HTTP errors
    users_data = response.json()
    return users_data

def get_country_from_ip(ip):
    response = requests.get(f'https://ipinfo.io/{ip}/json')
    data = response.json()
    country = data.get('country')
    print(f"IP: {ip}, Country: {country}")  # Debugging: Print IP and country
    return country

def convert_country_to_iso3(country_code):
    try:
        country = pycountry.countries.get(alpha_2=country_code)
        return country.alpha_3
    except AttributeError:
        return None                

# Load environment variables from .env file
load_dotenv()

# Manage logs
logging.basicConfig(filename=f'{LOGS_FOLDER}app.log', level=logging.DEBUG,
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
app.secret_key = os.getenv('APP_SECRET_KEY', 'your_secret_key')

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
    users_data = get_user_data()
    total_users = len(users_data)
    
    # Calculate the number of institutions
    domains = set()
    for user in users_data:
        email = user.get('email')
        if email:
            domain = email.split('@')[-1]
            domains.add(domain)
    total_institutions = len(domains)
    
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
    
    print(f"Country Counts: {country_counts}")  # Debugging: Print country counts
    
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

@app.route('/informations')
def informations():
    return render_template('informations.html')

@app.route('/upload', methods=['POST'])
def upload_file():
         
    if 'files[]' not in request.files:
        return jsonify({'message': 'No file found', 'status': 'error'}), 400
    
    files = request.files.getlist('files[]')
    uploaded_files = []
    rejected_files = []
    
    clear_logs(LOGS_FOLDER)
    delete_files_in_folder(UPLOAD_FOLDER)
    delete_files_in_folder(DOWNLOAD_FOLDER)
    
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
    getSegmentation(UPLOAD_FOLDER, f"{DOWNLOAD_FOLDER}output/")

    # Zip folder for download
    zip_folder(f"{DOWNLOAD_FOLDER}output", OUTPUT_ZIP)

    return jsonify({"message": "Segmentation completed", "download_url": "/download"}), 200

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
    clear_logs(LOGS_FOLDER)
    delete_files_in_folder(UPLOAD_FOLDER)
    delete_files_in_folder(DOWNLOAD_FOLDER)
    app.run(host='0.0.0.0', port=5000, debug=True)


# ----------------------------------------------------------------------------------------------
# MISC

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