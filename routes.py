from flask import Blueprint, current_app, session, render_template, redirect, url_for, request, flash, jsonify, send_file
import secrets, os, threading, pandas as pd, plotly.express as px
from urllib.parse import urlencode, quote_plus
from authlib.integrations.base_client.errors import OAuthError, MismatchingStateError
from werkzeug.utils import secure_filename

from utils import *
from main import getSegmentation
from app import oauth

from config import UPLOAD_FOLDER, DOWNLOAD_FOLDER, OUTPUT_ZIP

bp = Blueprint('routes', __name__)

high_scale_nb_users = 100

@bp.route("/")
def welcome():
    return render_template("welcomepage.html")

@bp.route("/callback", methods=["GET", "POST"])
def callback():
    try:
        token = oauth.auth0.authorize_access_token()
        state = session.pop('state', None)
        if request.args.get('state') != state:
            raise MismatchingStateError()
        nonce = session.pop('nonce', None)
        userinfo = oauth.auth0.parse_id_token(token, nonce=nonce)

        if not userinfo.get('email_verified'):
            return redirect(url_for('routes.verify_email'))

        session["user"] = userinfo
        return redirect(url_for('routes.segmentation'))
    except OAuthError as error:
        flash("Authentication failed: " + error.description)
        return redirect(url_for('routes.welcome'))

@bp.route("/verify_email")
def verify_email():
    return render_template("verify_email.html")

@bp.route("/login")
def login():
    nonce = secrets.token_urlsafe()
    state = secrets.token_urlsafe()
    session['nonce'] = nonce
    session['state'] = state
    return oauth.auth0.authorize_redirect(
        redirect_uri=url_for("routes.callback", _external=True),
        nonce=nonce,
        state=state
    )

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(
        "https://" + current_app.config['AUTH0_DOMAIN'] + "/v2/logout?" + urlencode(
            {
                "returnTo": url_for("routes.welcome", _external=True),
                "client_id": current_app.config['AUTH0_CLIENT_ID'],
            },
            quote_via=quote_plus,
        )
    )

@bp.route('/users')
def users():
    users_data = get_user_data()
    total_users = len(users_data)
    cases_processed = get_cases_processed()
    
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


@bp.route("/about")
def about():
    return render_template("about.html")

@bp.route("/faq")
def faq():
    return render_template("faq.html")

@bp.route("/segmentation")
def segmentation():
    if 'user' in session:
        return render_template('segmentation.html')
    return redirect(url_for('routes.login'))

@bp.route('/upload', methods=['POST'])
def upload_file():
         
    if 'files[]' not in request.files:
        return jsonify({'message': 'No file found', 'status': 'error'}), 400
    
    files = request.files.getlist('files[]')
    uploaded_files = []
    rejected_files = []
    
    clean_folders()  # Clear previous logs and files before uploading new ones
    
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)  # Use this werkzeug method to secure filename.
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)
            uploaded_files.append(filename)
        else:
            rejected_files.append(file.filename)
            
    upload_files(UPLOAD_FOLDER)
    
    if uploaded_files:
        message = f"Uploaded: {', '.join(uploaded_files)}"
        if rejected_files:
            message += f" | Rejected: {', '.join(rejected_files)}"
        return jsonify({'message': message, 'status': 'success'}), 200
    else:
        return jsonify({'message': 'No valid files uploaded', 'status': 'error'}), 400

@bp.route('/segment', methods=['POST'])
def segment():
    # Get user email from session or token
    user_email = session.get("user", {}).get("email", "unknown_user")
    
    # Run segmentation function
    getSegmentation(DOWNLOAD_FOLDER, user_email)

    # Zip folder for download
    zip_folder(DOWNLOAD_FOLDER, OUTPUT_ZIP)
        
    # Start background thread to copy files (only if output exists)
    has_output = (
        os.path.exists(DOWNLOAD_FOLDER) and
        any(fname.endswith(".nii.gz") for fname in os.listdir(DOWNLOAD_FOLDER))
    )

    if has_output:
        increment_cases_processed()
        # send_email(user_email, "A-eye segmentation task completed successfully. You can download the results.")
        threading.Thread(
            target=copy_segmentation_data,
            args=(user_email, "./nnUNet/nnUNet_inference/input", DOWNLOAD_FOLDER)
        ).start()
    else:
        # send_email(user_email, "A-eye segmentation task failed. Check the logs for details.")
        print("[A-eye] Segmentation failed or no .nii.gz output found. Data not copied!")

    return jsonify({"message": "Segmentation completed", "download_url": "/download"}), 200

@bp.route('/profile')
@requires_auth  # Ensure only logged-in users can view this
def profile():
    user = session.get("user")
    if not user:
        return redirect(url_for("routes.login"))

    return render_template("profile.html", user=user)

@bp.route('/download', methods=['GET'])
def download_files():
    if os.path.exists(OUTPUT_ZIP):
        return send_file(OUTPUT_ZIP, as_attachment=True)
    return "File not found", 404

@bp.route("/test-email")
def test_email():
    # Get user email from session or token
    user_email = session.get("user", {}).get("email", "unknown_user")
    to = user_email  # use your real address
    body = "This is a test email from A-eye."

    try:
        msg = Message(
            subject="Test Email",
            recipients=[to],
            body=body
        )
        mail.send(msg)
        return "Email sent successfully!", 200
    except Exception as e:
        return f"Failed to send email: {e}", 500