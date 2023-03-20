import os, glob, shutil, subprocess
import dicom2nifti
import argparse
import logging
from flask import redirect, url_for

# bools
enable_args = False
use_ext_folders = True

# logs folder
LOGS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs/')

# ----------------------------------------------------------------------------------------------
# MAIN FUNCTION

def getSegmentation(input=None):
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
        args_in = input # origin input folder
        args_out = '/home/jaimebarranco/Desktop/test_inference/output' # origin output folder

    # sudo_pwd = os.environ['SUDO_PWD']
    sudo_pwd = 'Patatahitech2.0'

    # nnUNet
    shm_size = 10 # shared memory (gb)
    abs_path = '/mnt/sda1/Repos/a-eye/a-eye_segmentation/deep_learning/nnUNet/nnUNet'
    rel_path = '/opt/nnunet_resources'
    aux_in = f'nnUNet_inference/temp_inference/input' # input aux folder
    aux_out = f'nnUNet_inference/temp_inference/output' # output aux folder

    start_docker()

    if use_ext_folders:
        # Copy content from origin input folder into local input folder
        if os.path.isdir(args_in):
            copy_folder(args_in, os.path.join(abs_path, aux_in))
        elif os.path.isfile(args_in):
            copy_file(args_in, os.path.join(abs_path, aux_in))
        # Create output aux folder if it doesn't exist
        if not os.path.exists(os.path.join(abs_path, aux_out)):
            os.makedirs(os.path.join(abs_path, aux_out))

    # Convert to nifti
    convert_to_nifti(os.path.join(abs_path, aux_in))

    # Check input filenames (need to be in nnUNet format (0000.nii.gz))
    check_filenames(os.path.join(abs_path, aux_in))

    # inference command terminal
    command = f' \
        docker run --rm \
        --gpus device=0 \
        --shm-size={shm_size}gb \
        -v {abs_path}:{rel_path} \
        petermcgor/nnunet:0.0.1 nnUNet_predict \
        -i {rel_path}/{aux_in} \
        -o {rel_path}/{aux_out} \
        -tr nnUNetTrainerV2 \
        -ctr nnUNetTrainerV2CascadeFullRes \
        -m 3d_fullres \
        -p nnUNetPlansv2.1 \
        -t Task313_Eye \
    '

    sudo_command = f'echo {sudo_pwd} | sudo -S -s {command}'
    # sudo_command = f'echo AEye mola mazo'

    # Print command
    print_and_log(f'[AEye] nnUNet inference command: {command}', 'info', LOGS_FOLDER)

    # Run command
    run_command_and_print_output(f'{sudo_command}')

    if use_ext_folders:
        # Copy aux output folder into origin output folder
        copy_folder(os.path.join(abs_path, aux_out), args_out)
        # Remove aux folders
        # delete_files_in_folder(os.path.join(abs_path, aux_in))
        # delete_files_in_folder(os.path.join(abs_path, aux_out))

    # DONE!
    print('[AEye] Inference finished!!')
    print_and_log('[AEye] Inference finished!!', 'info', LOGS_FOLDER)
    
    # Copy log files into output folder and remove content from log files
    if use_ext_folders:
        # Copy log files (log folder) into output folder
        copy_folder(LOGS_FOLDER, os.path.join(args_out, 'logs')) # logs folder in output
        # Remove content from log files
        # clear_logs(LOGS_FOLDER)

    return 'Inference finished!!'


# ---------------------------------------------------------------------------------------------
# AUX FUNCTIONS

def copy_folder(source, destination):
    if not os.path.exists(destination):
        os.mkdir(destination)
    for item in os.listdir(source):
        s = os.path.join(source, item)
        d = os.path.join(destination, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

def copy_file(source, destination):
    if not os.path.exists(destination):
        os.mkdir(destination)
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
            print_and_log(f"[AEye] Failed to delete {item_path}. Reason: {e}", 'error', LOGS_FOLDER)

def delete_folder(folder):
    shutil.rmtree(folder)

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
        print_and_log(f'[AEye] file name: {file_name}', 'info', LOGS_FOLDER)
        print_and_log(f'[AEye] file extension: {file_extension}', 'info', LOGS_FOLDER)
        print_and_log(f'[AEye] absolute file path: {file_path}', 'info', LOGS_FOLDER)
        if not str(file_name).endswith('_0000'):
            correct_filename(file_path, file_name, file_extension)

def correct_filename(file_path, file_name, file_extension):
    print_and_log('[AEye] Changing filename to nnUNet format...', 'info', LOGS_FOLDER)
    new_file_name = f'{file_name}_0000{file_extension}' # extension for nnUNet
    os.rename(file_path, os.path.join(os.path.dirname(file_path), new_file_name))

def convert_to_nifti(folder):
    # Get a list of all DICOM folders in the input folder
    dcm_folders = sorted([f.path for f in os.scandir(folder) if f.is_dir() and f.name != '.DS_Store'])
    if len(dcm_folders) >0:
        print_and_log('[AEye] Converting DICOM to NIfTI format...', LOGS_FOLDER)
        # Convert each DICOM folder to NIfTI format
        for dcm_folder in dcm_folders:
            filename = str(os.path.basename(dcm_folder) + '.nii.gz')
            dicom2nifti.dicom_series_to_nifti(dcm_folder, f'{folder}/{filename}', reorient_nifti=False)
            # cmd = ["dcm2niix", "-f", filename, "-z", "y", "-o", output_nifti_folder, input_dicom_folder]
            # process = subprocess.Popen(cmd, stdout=subprocess.PIPE)  # pass the list as input to Popen
            # _ = process.communicate()[0]  # the [0] is to return just the output, because otherwise it would be outs, errs = proc.communicate()
        # Remove DICOM folders
        for dcm_folder in dcm_folders:
            delete_folder(dcm_folder)

def start_docker():
    # Check if Docker is running and if not, initialize it
    try:
        # docker version
        run_command_and_print_output('docker version')
        print_and_log("[AEye] Docker is already running...", 'info', LOGS_FOLDER)
    except:
        # If Docker is not running...
        print_and_log("[AEye] Docker was not initialized!!", 'warning', LOGS_FOLDER)
        # ... start it!
        print_and_log("[AEye] Initializing docker...", 'info', LOGS_FOLDER)
        # docker start
        run_command_and_print_output('systemctl start docker')
        # sleep 10s
        run_command_and_print_output('sleep 10')
        print_and_log("[AEye] Docker has been started", 'info', LOGS_FOLDER)

def clear_logs(logs_folder=None):
    open(f'{logs_folder}app.log', 'w').close()
    open(f'{logs_folder}console.log','w').close()

def print_console(text=None, logs_folder=None):
    logs_file = f'{logs_folder}console.log'
    print(text, file=open(logs_file, 'a'))

def print_and_log(text=None, level='info', logs_folder=None):
    logs_file = f'{logs_folder}console.log'
    print(text, file=open(logs_file, 'a'))
    if level=='info':
        logging.info(text)
    elif level=='warning':
        logging.warning(text)
    elif level=='error':
        logging.error(text)

def run_command_and_print_output(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
    console_output, console_errors = process.communicate()
    console_output = console_output.decode('utf-8')
    for line in console_output.splitlines():
        print_console(line, LOGS_FOLDER)
    print_console(console_errors, LOGS_FOLDER)