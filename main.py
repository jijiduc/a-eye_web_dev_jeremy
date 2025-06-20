import os, glob, shutil, subprocess
import dicom2nifti
import argparse
import logging
from flask import redirect, url_for
import zipfile
import py7zr
import fnmatch

# bools
enable_args = False  # run the segmentation through the command line
use_ext_folders = True  # input and output folders

# logs folder
LOGS_FOLDER = "./logs"

# ----------------------------------------------------------------------------------------------
# MAIN FUNCTION

def getSegmentation(input=None, output=None):
    ''' Main function: performs inference on input folder and saves output in output folder. '''

    # input/output folders
    if enable_args:
        parser = argparse.ArgumentParser()
        parser.add_argument('-i', '--input', type=str, required=True, help='input folder')
        parser.add_argument('-o', '--output', type=str, required=True, help='output folder')
        args = parser.parse_args()
        args_in = args.input
        args_out = args.output
    else:
        args_in = input # origin input
        args_out = output # origin output folder


    # nnUNet
    shm_size = 10 # shared memory (gb)
    # abs_path = '/home/debi/jaime/repos/a-eye/a-eye_web/nnUNetv2/35subs'  # nnUNetv2 main folder
    abs_path = '/home/debi/jaime/repos/a-eye/a-eye_web/nnUNet'  # nnUNetv1 main folder
    rel_path = '/app/nnUNet'  # for the docker image
    aux_in = 'nnUNet_inference/input'  # input aux folder
    aux_out = 'nnUNet_inference/output'  # output aux folder

    start_docker()  # initialize docker for segmentation with GPU

    if use_ext_folders:
        # Copy content from origin input folder into local input folder
        if os.path.isdir(args_in):
            copy_folder(args_in, os.path.join(abs_path, aux_in))
        elif os.path.isfile(args_in): # local
            # Manage zip files
            type = args_in.split('.')[-1].lower()
            if type == 'zip' or type == '7z':
                unzip_file(type, args_in, os.path.join(abs_path, aux_in))
            else:
                copy_file(args_in, os.path.join(abs_path, aux_in))
        # Create output aux folder if it doesn't exist
        if not os.path.exists(os.path.join(abs_path, aux_out)):
            os.makedirs(os.path.join(abs_path, aux_out))

    # Check dicom folders names
    check_dicom_folders_names(os.path.join(abs_path, aux_in))

    # Check input filenames (need to be in nnUNet format (0000.nii.gz))
    check_filenames(os.path.join(abs_path, aux_in))

    # inference command terminal (nnUNetv2)
    # command = f' \
    # docker run --rm \
    # --gpus all \
    # --shm-size={shm_size}gb \
    # -v {abs_path}:{rel_path} \
    # jaimebarran/nnunet:0.1.0 \
    # nnUNetv2_predict \
    # -d Dataset313_Eye \
    # -i {rel_path}/{aux_in} \
    # -o {rel_path}/{aux_out} \
    # -f 0 1 2 3 4 \
    # -tr nnUNetTrainer \
    # -c 3d_fullres \
    # -p nnUNetPlans \
    # '

    # inference command terminal (nnUNetv1)
    command = f' \
    docker run --rm \
    --gpus all \
    --shm-size={shm_size}gb \
    --entrypoint=/bin/bash \
    -v {abs_path}:{rel_path} \
    jaimebarran/fw_gear_aeye:0.0.1 \
    -c "nnUNet_predict \
    -i {rel_path}/{aux_in} \
    -o {rel_path}/{aux_out} \
    -tr nnUNetTrainerV2 \
    -ctr nnUNetTrainerV2CascadeFullRes \
    -m 3d_fullres \
    -p nnUNetPlansv2.1 \
    -t Task313_Eye" \
    '

    # Print command
    print_and_log(f'[A-eye] nnUNet inference command: {command}', 'info', LOGS_FOLDER)

    # Run command
    run_command_and_print_output(f'{command}')

    # DONE!
    print('[A-eye] Inference finished!!')
    print_and_log('[A-eye] Inference finished!!', 'info', LOGS_FOLDER)
    
    # Copy files into output folder and clean folders
    if use_ext_folders:
        # Copy aux output folder into origin output folder
        # copy_folder(os.path.join(rel_path, aux_out), args_out)
        
        # Copy log files (log folder) into output folder
        copy_folder(LOGS_FOLDER, os.path.join(args_out, 'logs')) # logs folder in output
        
        # Remove content in aux folders
        # delete_files_in_folder(os.path.join(rel_path, aux_in))
        # delete_files_in_folder(os.path.join(rel_path, aux_out))
        
        # Remove content from log files
        # clear_logs(LOGS_FOLDER)

    return 'Inference finished!!'


# ---------------------------------------------------------------------------------------------
# AUX FUNCTIONS

def unzip_file(type, source, destination):
    if type == 'zip':
        # Create a ZipFile object with the path of the zip file
        zip_file = zipfile.ZipFile(source)
        # Extract all the files to a folder
        zip_file.extractall(destination)
        print_and_log(f'[A-eye] Unzipping file: {source}', 'info', LOGS_FOLDER)
        # Close the zip file
        zip_file.close()
    elif type == '7z':
        # Open the .7z archive file
        with py7zr.SevenZipFile(source, mode='r') as archive:
            # Extract all contents to the current directory
            archive.extractall(path=destination)


def copy_folder(source, destination):
    os.makedirs(destination, exist_ok=True)
    for item in os.listdir(source):
        s = os.path.join(source, item)
        d = os.path.join(destination, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            type = s.split('.')[-1].lower()
            if type == 'zip' or type == '7z':
                unzip_file(type, s, destination)
            else:
                shutil.copy2(s, d)

def copy_file(source, destination):
    os.makedirs(destination, exist_ok=True)
    shutil.copy(source, destination)

def delete_files_in_folder(folder):
    for item in os.listdir(folder):
        item_path = os.path.join(folder, item)
        try:
            if os.path.isdir(item_path):
                shutil.rmtree(item_path)
            elif os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
        except Exception as e:
            print_and_log(f"[A-eye] Failed to delete {item_path}. Reason: {e}", 'error', LOGS_FOLDER)

def delete_folder(folder):
    shutil.rmtree(folder)

def check_dicom_folders_names(folder):
    # Get a list of all DICOM folders in the input folder
    dicom_folders = find_dicom_folders(folder)
    # Check dicom folders names
    if not dicom_folders:
        print_and_log('[AEye] No DICOM folders found.', 'info', LOGS_FOLDER)
        return
    else:
        print_and_log('[AEye] Checking DICOM folders names...', 'info', LOGS_FOLDER)
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
            convert_to_nifti(folder, dicom_folders)

def check_filenames(folder):
    file_paths = glob.glob(f'{folder}/*.nii.gz')
    for file_path in file_paths:
        file_extensions = []
        while True:
            file_path, ext = os.path.splitext(file_path)
            if ext:
                file_extensions.insert(0, ext)
            else:
                break
        file_extension = ''.join(file_extensions)
        file_name = os.path.basename(file_path)
        file_path = f'{file_path}{file_extension}'
        print_and_log(f'[A-eye] file name: {file_name}', 'info', LOGS_FOLDER)
        print_and_log(f'[A-eye] file extension: {file_extension}', 'info', LOGS_FOLDER)
        print_and_log(f'[A-eye] absolute file path: {file_path}', 'info', LOGS_FOLDER)
        if not str(file_name).endswith('_0000'):
            correct_filename(file_path, file_name, file_extension)

def correct_filename(file_path, file_name, file_extension):
    print_and_log('[A-eye] Changing filename to nnUNet format...', 'info', LOGS_FOLDER)
    new_file_name = f'{file_name}_0000{file_extension}' # extension for nnUNet
    print_and_log(f'[AEye] New filename = {new_file_name}', 'info', LOGS_FOLDER)
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
        # Remove DICOM folders
        for dicom_folder in dicom_folders:
            delete_folder(dicom_folder)

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
        print_and_log("[A-eye] Docker is already running...", 'info', LOGS_FOLDER)
    except:
        # If Docker is not running...
        print_and_log("[A-eye] Docker was not initialized!!", 'warning', LOGS_FOLDER)
        # ... start it!
        print_and_log("[A-eye] Initializing docker...", 'info', LOGS_FOLDER)
        # docker start
        run_command_and_print_output('systemctl start docker')
        # sleep 10s
        run_command_and_print_output('sleep 10')
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