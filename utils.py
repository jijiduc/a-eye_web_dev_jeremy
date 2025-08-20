import os
import re
import glob
import json
import shutil
import subprocess
import dicom2nifti
import logging
import zipfile
import py7zr
import fnmatch
import requests
import pycountry
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import wraps
from flask import redirect, url_for, session, current_app
import threading
import requests
from app import mail
from flask_mail import Message
from string import Template
import gzip
from config import (
    DATA_FOLDER,
    LOGS_FOLDER,
    DOWNLOAD_FOLDER,
    ALLOWED_EXTENSIONS,
    STATS_FILE
)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def zip_folder(folder_path, output_path):
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), folder_path))


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


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


def copy_segmentation_data(user_email, input, output):
    zurich_time = datetime.now(ZoneInfo("Europe/Zurich"))
    timestamp = zurich_time.strftime("%Y%m%d_%H%M")
    safe_email = user_email.replace("@", "_at_").replace(".", "_")
    dest_dir = f"{DATA_FOLDER}/{safe_email}_{timestamp}"

    os.makedirs(dest_dir, exist_ok=True)
    
    input_dest = os.path.join(dest_dir, "input")
    output_dest = os.path.join(dest_dir, "output")

    copy_folder(input, input_dest)
    copy_folder(output, output_dest)
    
    print(f"Copied segmentation data to {dest_dir}")


def unzip_file(file_type, source, destination):
    try:
        os.makedirs(destination, exist_ok=True)

        if file_type == 'zip':
            print_and_log(f'[A-eye] Unzipping ZIP file: {source}', 'info', LOGS_FOLDER)
            with zipfile.ZipFile(source, 'r') as zip_ref:
                abs_dest = os.path.abspath(destination)

                for member in zip_ref.namelist():
                    member_path = os.path.abspath(os.path.join(destination, member))
                    if not os.path.commonpath([abs_dest, member_path]) == abs_dest:
                        raise Exception(f"Unsafe path in zip file: {member}")

                zip_ref.extractall(destination)

        elif file_type == '7z':
            print_and_log(f'[A-eye] Unzipping 7z file: {source}', 'info', LOGS_FOLDER)
            with py7zr.SevenZipFile(source, mode='r') as archive:
                archive.extractall(path=destination)

        else:
            raise ValueError(f"Unsupported archive type: {file_type}")

    except Exception as e:
        print_and_log(f'[A-eye] Error unzipping file {source}: {e}', 'error', LOGS_FOLDER)
        raise


def copy_folder(source, destination):
    os.makedirs(destination, exist_ok=True)
    for item in os.listdir(source):
        s = os.path.join(source, item)
        d = os.path.join(destination, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)


def copy_clean_files(src_folder, dst_folder):
    """
    Copy only *_0000.nii.gz files from src_folder (and subfolders)
    into dst_folder (flat, no subfolder structure).
    """
    os.makedirs(dst_folder, exist_ok=True)

    for root, _, files in os.walk(src_folder):
        for f in files:
            if f.endswith("_0000.nii.gz"):
                src_path = os.path.join(root, f)
                dest_path = os.path.join(dst_folder, f)

                # Avoid overwriting if two files have the same name
                if os.path.exists(dest_path):
                    base, ext = os.path.splitext(f)
                    dest_path = os.path.join(dst_folder, f"{base}_dup{ext}")

                shutil.copy2(src_path, dest_path)


def copy_file(source, destination):
    os.makedirs(destination, exist_ok=True)
    shutil.copy(source, destination)


def move_file(pattern, destination):
    os.makedirs(destination, exist_ok=True)
    for file_path in glob.glob(pattern):
        shutil.move(file_path, destination)


def copy_file_hpc(source, destination):
    print_and_log(f"[A-eye] Copying files from {source} to {destination}...", 'info', LOGS_FOLDER)
    os.system(f'scp {source} {destination}')


def copy_folder_hpc(source, destination):
    print_and_log(f"[A-eye] Copying files from {source} to {destination}...", 'info', LOGS_FOLDER)
    os.system(f'scp -r {source} {destination}')


def copy_files_in_folder_hpc(source, destination):
    print_and_log(f"[A-eye] Copying files from {source} to {destination}...", 'info', LOGS_FOLDER)
    os.system(f'scp {source}/* {destination}')


def delete_files_in_folder(folder):
    for root, dirs, files in os.walk(folder):
        for file in files:
            try:
                os.remove(os.path.join(root, file))
            except Exception as e:
                print_and_log(f"[A-eye] Failed to delete {folder}. Reason: {e}", 'error', LOGS_FOLDER)


def delete_folder(folder):
    shutil.rmtree(folder)
    

def delete_subfolders(folder):
    for item in os.listdir(folder):
        item_path = os.path.join(folder, item)
        if os.path.isdir(item_path):
            try:
                shutil.rmtree(item_path)
            except Exception as e:
                print_and_log(f"[A-eye] Failed to delete {item_path}. Reason: {e}", 'error', LOGS_FOLDER)


def check_dicom_folders_names(folder):
    # Get a list of all DICOM folders in the input folder
    dicom_folders = find_dicom_folders(folder)
    # Check dicom folders names
    if not dicom_folders:
        print_and_log('[A-eye] No DICOM folders found.', 'info', LOGS_FOLDER)
        return
    else:
        print_and_log('[A-eye] Checking DICOM folders names...', 'info', LOGS_FOLDER)
        for dicom_folder in dicom_folders:
            dicom_folder_name = os.path.basename(dicom_folder)
            parent_folder_path = os.path.dirname(dicom_folder)
            parent_folder_name = os.path.basename(parent_folder_path)
            # Check if dicom_folder name already starts with parent_folder_name
            if not dicom_folder_name.startswith(parent_folder_name):
                new_folder_name = parent_folder_name + '_' + dicom_folder_name
                new_folder_path = os.path.join(parent_folder_path, new_folder_name)
                os.rename(dicom_folder, new_folder_path)
            # Convert to nifti
            convert_to_nifti(folder)


def check_nifti_files(folder):
    for file_path in glob.glob(os.path.join(folder, '**', '*.nii'), recursive=True):
        gz_path = file_path + '.gz'
        with open(file_path, 'rb') as f_in, gzip.open(gz_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)


def check_filenames(folder):
    for file_path in glob.glob(os.path.join(folder, '**', '*'), recursive=True):   # catch any case; we'll filter below
        # only operate on files that end with .nii.gz (case-insensitive)
        if not file_path.lower().endswith('.nii.gz'):
            continue

        original_basename = os.path.basename(file_path)   # e.g. "x_...1.000.nii.gz"
        base_no_ext = original_basename[:-len('.nii.gz')] # e.g. "x_...1.000"
        file_extension = '.nii.gz'

        print_and_log(f'[A-eye] file name: {original_basename}', 'info', LOGS_FOLDER)
        print_and_log(f'[A-eye] file base (no ext): {base_no_ext}', 'info', LOGS_FOLDER)
        print_and_log(f'[A-eye] file extension: {file_extension}', 'info', LOGS_FOLDER)
        print_and_log(f'[A-eye] absolute file path: {file_path}', 'info', LOGS_FOLDER)

        if not base_no_ext.endswith('_0000'):
            # pass base without extension so correct_filename can build: base_no_ext + '_0000' + '.nii.gz'
            correct_filename(file_path, base_no_ext, file_extension)


def correct_filename(file_path, file_name, file_extension):
    print_and_log('[A-eye] Changing filename to nnUNet format...', 'info', LOGS_FOLDER)
    new_file_name = f'{file_name}_0000{file_extension}' # extension for nnUNet
    print_and_log(f'[A-eye] New filename = {new_file_name}', 'info', LOGS_FOLDER)
    os.rename(file_path, os.path.join(os.path.dirname(file_path), new_file_name))


def convert_to_nifti(folder):
    # Get a list of all DICOM folders in the input folder
    dicom_folders = find_dicom_folders(folder)
    if len(dicom_folders) > 0:
        print_and_log('[A-eye] Converting DICOM to NIfTI format...', 'info', LOGS_FOLDER)
        # Convert each DICOM folder to NIfTI format
        for dicom_folder in dicom_folders:
            filename = str(os.path.basename(dicom_folder) + '.nii.gz')
            dicom2nifti.dicom_series_to_nifti(dicom_folder, f'{folder}/{filename}', reorient_nifti=True)
            # cmd = ["dcm2niix", "-f", filename, "-z", "y", "-o", output_nifti_folder, input_dicom_folder]
            # process = subprocess.Popen(cmd, stdout=subprocess.PIPE)  # pass the list as input to Popen
            # _ = process.communicate()[0]  # the [0] is to return just the output, because otherwise it would be outs, errs = proc.communicate()
            # delete_folder(folder)  # Delete the original DICOM folder after conversion


def find_dicom_folders(root_path):
    dicom_folders = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        for filename in filenames:
            if fnmatch.fnmatch(filename, '*.dcm'):
                dicom_folders.append(dirpath)
                break

    return dicom_folders


def start_docker():
    # Check if Docker is running and if not, initialize it
    try:
        # docker version
        run_command_and_print_output('docker version')
        print_and_log("\n[A-eye] Docker is already running...", 'info', LOGS_FOLDER)
    except:
        # If Docker is not running...
        print_and_log("[A-eye] Docker was not initialized!!", 'warning', LOGS_FOLDER)
        # ... start it!
        print_and_log("[A-eye] Initializing docker...", 'info', LOGS_FOLDER)
        # docker start
        run_command_and_print_output('systemctl start docker')
        # sleep 1s
        run_command_and_print_output('sleep 1')
        print_and_log("[A-eye] Docker has been started", 'info', LOGS_FOLDER)


def clear_logs(logs_folder=None):
    open(f'{logs_folder}/app.log', 'w').close()
    open(f'{logs_folder}/console.log','w').close()


def print_console(text=None, logs_folder=None):
    logs_file = f'{logs_folder}/console.log'
    print(text, file=open(logs_file, 'a'))


def print_and_log(text=None, level='info', logs_folder=None):
    logs_file = f'{logs_folder}/console.log'
    print(text, file=open(logs_file, 'a'))
    if level=='info':
        logging.info(text)
    elif level=='warning':
        logging.warning(text)
    elif level=='error':
        logging.error(text)


def run_command_and_print_output(command):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Redirect stderr to stdout
        shell=True
    )
    console_output, console_errors = process.communicate()
    
    if console_output:
        console_output = console_output.decode('utf-8')
        for line in console_output.splitlines():
            print_console(line, LOGS_FOLDER)

    if console_errors:
        console_errors = console_errors.decode('utf-8')
        for line in console_errors.splitlines():
            print_console(line, LOGS_FOLDER)


def clean_folders():
    clear_logs(LOGS_FOLDER)  # Clear previous logs
    delete_files_in_folder(f'{DOWNLOAD_FOLDER}/logs')  # Clear previous logs in download folder
    delete_files_in_folder("static/upload")  # Clear static/upload folder
    delete_subfolders("static/upload") # Clear previous uploaded files
    delete_files_in_folder("nnUNet/nnUNet_inference")  # Clear output.zip
    delete_files_in_folder("nnUNet/nnUNet_inference/input")  # Clear previous inference files
    delete_subfolders("nnUNet/nnUNet_inference/input")  # Clear previous uploaded files
    delete_files_in_folder("nnUNet/nnUNet_inference/output")  # Clear previous inference output
    


def get_management_api_token():
    url = f'https://{current_app.config["AUTH0_DOMAIN"]}/oauth/token'
    payload = {
        'client_id': current_app.config['AUTH0_CLIENT_ID'],
        'client_secret': current_app.config['AUTH0_CLIENT_SECRET'],
        'audience': f'https://{current_app.config["AUTH0_DOMAIN"]}/api/v2/',
        'grant_type': 'client_credentials'
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()['access_token']


def get_user_data():
    auth0_domain = current_app.config['AUTH0_DOMAIN']
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


# def send_email_async(to, body):
#     threading.Thread(target=send_email, args=(to, body)).start()


def send_email(to, body):
    with current_app.app_context():
        msg = Message(
            subject='Segmentation Task Completed',
            recipients=[to],
            body=body
        )
        mail.send(msg)


def load_stats():
    if not os.path.exists(STATS_FILE):
        return {"cases_processed": 0}
    with open(STATS_FILE, "r") as f:
        return json.load(f)


def increment_cases_processed():
    stats = load_stats()
    stats["cases_processed"] += 1
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)


def get_cases_processed():
    return load_stats()["cases_processed"]


def modify_jobfile(template_file, user_email, timestamp, output_file):
    """Modify the jobfile template with user-specific information."""
    
    # Make the email safe for paths
    safe_email = re.sub(r'[@.]', '_', user_email)

    # Base results dir
    base_results_dir = "/home/jaime.barrancohernandez/results/nnunet"

    # Create unique folder for this user + timestamp
    user_dir = os.path.join(base_results_dir, f"{safe_email}_{timestamp}")
    os.system(f"ssh jaime.barrancohernandez@chacha 'mkdir -p {user_dir}'")

    # Read the template
    with open(template_file, "r") as f:
        template = Template(f.read())
        job_script = template.safe_substitute(MAIL_USER=user_email)

    # Update SBATCH output/error paths
    out_file = f"{user_dir}/{safe_email}_{timestamp}_nnUNet_predict.%N.%j.%a.out"
    err_file = f"{user_dir}/{safe_email}_{timestamp}_nnUNet_predict.%N.%j.%a.err"
    job_script = re.sub(r'(#SBATCH --output=).+\.out', rf'\1{out_file}', job_script)
    job_script = re.sub(r'(#SBATCH --error=).+\.err', rf'\1{err_file}', job_script)

    # Update the specific --bind line
    job_script = re.sub(
        r'--bind\s+/home/jaime\.barrancohernandez/results/nnunet:/output',
        f"--bind {user_dir}:/output",
        job_script
    )

    # Write modified jobfile
    with open(output_file, "w") as f:
        f.write(job_script)


def upload_files(UPLOAD_FOLDER):
    # paths
    rel_path = './nnUNet'  # for the docker image
    aux_in = 'nnUNet_inference/input'  # input aux folder (inside rel_path)
    input_hpc = 'jaime.barrancohernandez@chacha:/home/jaime.barrancohernandez/shared_datasets/nnunet/nnUNet/nnUNet_inference'
    
    local_aux_in = os.path.join(rel_path, aux_in)

    # 1. Check if input folder contains zip/7z files and unzip them
    if os.path.isdir(UPLOAD_FOLDER):
        for file in os.listdir(UPLOAD_FOLDER):
            fpath = os.path.join(UPLOAD_FOLDER, file)
            if os.path.isfile(fpath):
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.zip', '.7z']:
                    unzip_file(ext[1:], fpath, UPLOAD_FOLDER)  # unzip into the same input folder

    # 2. Check dicom folders
    check_dicom_folders_names(UPLOAD_FOLDER)

    # 3. Check nifti files
    check_nifti_files(UPLOAD_FOLDER)

    # 4. Check filenames
    check_filenames(UPLOAD_FOLDER)

    # 5. Copy the final results to rel_path+aux_in
    copy_clean_files(UPLOAD_FOLDER, local_aux_in)

    # 6. Copy rel_path+aux_in to input_hpc
    copy_folder_hpc(local_aux_in, input_hpc)
