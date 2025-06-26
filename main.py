import os
from utils import (
    start_docker,
    unzip_file,
    copy_file,
    copy_folder,
    check_dicom_folders_names,
    check_filenames,
    run_command_and_print_output,
    print_and_log
)
from config import LOGS_FOLDER

# ----------------------------------------------------------------------------------------------
# MAIN FUNCTION

def getSegmentation(input=None, output=None):
    ''' Main function: performs inference on input folder and saves output in output folder. '''

    # nnUNet
    shm_size = 10 # shared memory (gb)
    # abs_path = '/home/debi/jaime/repos/a-eye/a-eye_web/nnUNetv2/35subs'  # nnUNetv2 main folder
    abs_path = '/home/debi/jaime/repos/a-eye/a-eye_web/nnUNet'  # nnUNetv1 main folder
    rel_path = '/app/nnUNet'  # for the docker image
    aux_in = 'nnUNet_inference/input'  # input aux folder
    aux_out = 'nnUNet_inference/output'  # output aux folder

    # Check docker is running
    start_docker()
    
    # Copy content from origin input folder into local input folder
    if os.path.isfile(input):
        ext = os.path.splitext(input)[1].lower()
        if ext in ['.zip', '.7z']:
            unzip_file(ext[1:], input, os.path.join(rel_path, aux_in))  # ext[1:] removes the dot
        else:  # .nii.gz or other compressed files
            copy_file(input, os.path.join(rel_path, aux_in))
    elif os.path.isdir(input):
        copy_folder(input, os.path.join(rel_path, aux_in))

    # Create output aux folder if it doesn't exist
    os.makedirs(os.path.join(rel_path, aux_out), exist_ok=True)

    # Check dicom folders names
    check_dicom_folders_names(os.path.join(rel_path, aux_in))

    # Check input filenames (need to be in nnUNet format (0000.nii.gz))
    check_filenames(os.path.join(rel_path, aux_in))

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
    
    # Copy logs
    copy_folder(LOGS_FOLDER, os.path.join(output, 'logs'))  # needed for app.log

    return 'Inference finished!!'
