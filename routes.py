import os
import secrets
import shutil
import subprocess
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus, urlencode

import pandas as pd
import plotly.express as px
from authlib.integrations.base_client.errors import MismatchingStateError, OAuthError
from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from app import oauth
from config import LOGS_FOLDER
from main import getSegmentation
from models import UserPaths
from utils import (
    Message,
    allowed_file,
    cancel_slurm_job,
    clean_folders,
    convert_country_to_iso3,
    copy_segmentation_data,
    extract_nifti_metadata,
    get_cases_processed,
    get_country_from_ip,
    get_user_data,
    get_user_paths,
    increment_cases_processed,
    mail,
    print_and_log,
    requires_auth,
    sync_logs_to_output,
    upload_files,
    zip_folder,
)


def _cancel_job(paths: UserPaths) -> None:
    """Internal function canceling Slurm job

    Args:
        paths (UserPaths): initialized paths for the concerned user
    """
    if not paths.active_job_file.exists():
        return
    job_id = paths.active_job_file.read_text().strip()
    paths.active_job_file.unlink(missing_ok=True)
    
    if job_id:
        print_and_log(f"[A-eye] Cancelling Slurm job {job_id}...", 'warning', LOGS_FOLDER)
        try:
            cancel_slurm_job(job_id)
        except Exception:
            current_app.logger.exception("Failed to cancel Slurm job %s", job_id)

bp = Blueprint('routes', __name__)

high_scale_nb_users = 100

@bp.route("/") # In flask, by default a route only answer to GET request. 
# Need to use the methods arguments of the route() decorator to handlie different/multiple HTTP methods.
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

        session["user"] = userinfo # stores user in session
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
    redirect_uri = current_app.config.get("AUTH0_CALLBACK_URL") or url_for("routes.callback", _external=True)
    return oauth.auth0.authorize_redirect(
        redirect_uri=redirect_uri,
        nonce=nonce,
        state=state
    )

@bp.route("/logout")
def logout():
    session.clear()
    return_to = current_app.config.get("AUTH0_LOGOUT_URL") or url_for("routes.welcome", _external=True)
    return redirect(
        "https://" + current_app.config['AUTH0_DOMAIN'] + "/v2/logout?" + urlencode(
            {
                "returnTo": return_to,
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
    
    # Create a DataFrame for the country data
    df = pd.DataFrame(list(country_counts.items()),
                           columns=['Country', 'Count'])
    
    # Generate the choropleth map
    fig = px.choropleth(df, locations="Country",
                        locationmode='ISO-3', color="Count",
                        color_continuous_scale="Greens",
                        range_color=(0, high_scale_nb_users))

    fig.update_layout(
        autosize=True,
        margin={"r":0,"t":0,"l":0,"b":0},
        dragmode=False,
        geo=dict(
            showframe=False,
            showcoastlines=False,
            projection_type='equirectangular',
            lataxis=dict(range=[-90, 90]),
            lonaxis=dict(range=[-180, 180]),
            center=dict(lat=0, lon=0)
        ),
        coloraxis_showscale=False
    )

    map_html = fig.to_html(full_html=False, config={'responsive': True})
    
    return render_template('users.html', 
                           total_users=total_users,
                           cases_processed=cases_processed, 
                           total_institutions=total_institutions, 
                           map_html=map_html)


@bp.route("/about")
def about():
    return render_template("about.html")


@bp.route("/faq")
def faq():
    return render_template("faq.html")


@bp.route("/segmentation")
def segmentation():
    if 'user' in session:
        user_email: str = session.get("user", {}).get("email", "unknown_user")
        _cancel_job(get_user_paths(user_email))
        return render_template('segmentation.html')
    return redirect(url_for('routes.login'))


@bp.route('/upload', methods=['POST'])
def upload_file() -> tuple[Response, int]:
    """File upload handling for the user logged-in

      1. clear the user's previous data 
      2. saves provided files locally 
      3. copy them to the HPC input directory

      Returns:
          tuple[Response, int]: JSON response with upload and HTTP status code
      """
    user_email: str = session.get("user", {}).get("email", "unknown_user")
    paths: UserPaths = get_user_paths(user_email)

    _cancel_job(paths)

    if 'files[]' not in request.files:
        return jsonify({
            'message': 'No file found',
            'status': 'error'
            }), 400

    files = request.files.getlist('files[]')
    uploaded_files = []
    rejected_files = []

    try:
        # 1. clear the user's previous data 
        clean_folders(user_email)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        current_app.logger.exception("Could not prepare HPC folders for upload")
        return jsonify({
            'message': 'Could not reach the HPC over SSH to prepare the upload.'
                'Please try again once chacha/disco SSH access is available.',
            'status': 'error',
            'error': str(error)
        }), 503

    # 2. Save provided files locally and extract their metadata
    metadata : dict[str, dict] = {}
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)  # werkzeug sanitisation
            filepath = paths.upload / filename
            file.save(filepath)
            uploaded_files.append(filename)
            metadata[filename] = extract_nifti_metadata(str(filepath))
        else:
            rejected_files.append(file.filename)

    try:
        # 3. copy the provided files in the HPC input directory
        upload_files(paths.upload, paths.aux_input, paths.hpc_base_input)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        current_app.logger.exception("Could not copy uploaded files to HPC")
        return jsonify({
            'message': 'Files were received locally,'
                       ' but could not be copied to the HPC over SSH.'
            ' Please try again once chacha/disco SSH access is available.',
            'status': 'error',
            'error': str(error)
        }), 503

    if uploaded_files:
        message = f"Uploaded: {', '.join(uploaded_files)}"
        if rejected_files:
            message += f" | Rejected: {', '.join(rejected_files)}"
        return jsonify({
            'message': message,
            'status': 'success',
            'metadata': metadata,
            }), 200
    else:
        return jsonify({
            'message': 'No valid files uploaded',
            'status': 'error'
            }), 400


@bp.route('/segment', methods=['POST'])
def segment() -> tuple[Response, int]:
    """Run the segmentation pipeline for the logged-in user.

    1. submits the HPC job and waits for completion
    2. zips the output if existing
    3. starts a background thread to copy results to Filer01

    Returns:
        tuple[Response, int]: JSON response with status message and code.
        200 on success - 500 if the pipeline raised error
    """
    user_email: str = session.get("user", {}).get("email", "unknown_user")
    paths: UserPaths = get_user_paths(user_email)

    _cancel_job(paths)

    def store_job_id(job_id: str) -> None:
        """Store the job id

        Args:
            job_id (str): Slurm job ID
        """
        paths.active_job_file.parent.mkdir(parents=True, exist_ok=True)
        paths.active_job_file.write_text(job_id)

    try:
        getSegmentation(user_email, paths, ongoing_job_id=store_job_id)
    except Exception as error:
        paths.active_job_file.unlink(missing_ok=True)
        print_and_log(f"[A-eye] Segmentation failed: {error}",
                       'error', LOGS_FOLDER)
        sync_logs_to_output(paths.download)
        clean_folders(user_email)
        return jsonify({"message": "Segmentation failed",
                         "error": str(error)}), 500

    paths.active_job_file.unlink(missing_ok=True)

    has_output = (
        paths.download.exists() and
        any(fname.endswith(".nii.gz") for fname in os.listdir(paths.download))
    )

    if has_output:
        print_and_log("[A-eye] Copying segm. data to Filer01...",
                       'info', LOGS_FOLDER)
        sync_logs_to_output(paths.download)

    # 2. Zip folder for download
    zip_folder(paths.download, paths.output_zip)
        
    # 3. Start background thread to copy files (only if output exists)
    
    if has_output:
        increment_cases_processed()
        # send_email(user_email, "A-eye segmentation task completed successfully. You can download the results.")
        threading.Thread(
            target=copy_segmentation_data,
            args=(user_email, paths.aux_input, paths.download)
        ).start()
    else:
        # send_email(user_email, "A-eye segmentation task failed. Check the logs for details.")
        print_and_log("[A-eye] Segmentation failed or no .nii.gz output found" +
                      "Data not copied!",
                       'error', LOGS_FOLDER)
        sync_logs_to_output(paths.download)
        clean_folders(user_email)

    # 4. add result file and metadata
    result: list = []

    try:
        for file_name in sorted(os.listdir(paths.download)):
            if file_name.endswith('.nii.gz'):
                input_name = file_name.replace('.nii.gz', '_0000.nii.gz')
                shutil.copy2(paths.aux_input / input_name, paths.download / input_name)
                result.append({
                    'name': file_name,
                    'metadata': next(iter(extract_nifti_metadata(str(paths.download / file_name)).values()), {}),
                    'input_name': input_name,
                })
    except FileNotFoundError as error:
        current_app.logger.exception("Missing input file while collecting segmentation results")
        return jsonify({"message": f"Segmentation completed but an input file was missing: {error}"}), 500
    except Exception as error:
        current_app.logger.exception("Error collecting segmentation results")
        return jsonify({"message": f"Segmentation completed but results could not be collected: {error}"}), 500

    return jsonify({"message": "Segmentation completed",
                     "download_url": "/download",
                     "result": result}), 200


@bp.route('/profile')
@requires_auth  # Ensure only logged-in users can view this
def profile():
    user = session.get("user")
    if not user:
        return redirect(url_for("routes.login"))

    return render_template("profile.html", user=user)


@bp.route('/download', methods=['GET'])
def download_files() -> Response | tuple[str, int]:
    """Download the ZIP file generated for the user logged in

    Returns:
        Response: The ZIP file
        tuple[str, int]: A "File not found" error message with HTTP 404
    """
    user_email: str = session.get("user", {}).get("email", "unknown_user")
    paths: UserPaths = get_user_paths(user_email)
    if paths.output_zip.exists():
        safe_email = user_email.replace("@", "_").replace(".", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_name = f"output_{safe_email}_{timestamp}.zip"
        return send_file(paths.output_zip,
                         as_attachment=True,
                         download_name=download_name)
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

@bp.route('/result/<filename>', methods=['GET'])
def serve_result(filename: str):
    # check that the logged in user try to access
    if 'user' not in session:
        return jsonify({'message': 'Unauthorized'}), 401

    user_email: str = session.get("user", {}).get("email", "unknown_user")
    file_path: Path = (get_user_paths(user_email).download / filename)

    return send_file(file_path, mimetype='application/gzip')
