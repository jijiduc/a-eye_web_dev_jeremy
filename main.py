import os
from utils import *
from config import LOGS_FOLDER, UPLOAD_FOLDER, DOWNLOAD_FOLDER

# ----------------------------------------------------------------------------------------------
# MAIN FUNCTION

def getSegmentation(user_email):
    ''' Main function: performs inference on input folder and saves output in output folder. '''

    # nnUNet
    input = UPLOAD_FOLDER
    output = DOWNLOAD_FOLDER
    input_hpc = 'jaime.barrancohernandez@chacha:/home/jaime.barrancohernandez/shared_datasets/nnunetv1/nnUNet/nnUNet_inference/input'
    output_hpc = 'jaime.barrancohernandez@chacha:/home/jaime.barrancohernandez/results/nnunetv1'
    jobfile = 'jobfiles/nnunetv1_inference.sh'
    jobfile_hpc = 'jaime.barrancohernandez@chacha:/home/jaime.barrancohernandez/shared_datasets/nnunetv1/nnunetv1_inference.sh'

    # Check dicom folders names
    check_dicom_folders_names(input)

    # Check input filenames (need to be in nnUNet format (0000.nii.gz))
    check_filenames(input)

    # Copy content from origin input folder into local input folder
    if os.path.isfile(input):
        ext = os.path.splitext(input)[1].lower()
        if ext in ['.zip', '.7z']:
            unzip_file(ext[1:], input, input_hpc)  # ext[1:] removes the dot
        else:  # .nii.gz or other compressed files
            copy_file_hpc(input, input_hpc)
    elif os.path.isdir(input):
        copy_folder_hpc(input, input_hpc)

    # modify jobfile
    modify_jobfile(jobfile, user_email)
        
    # copy jobfile to hpc
    copy_file_hpc('nnunetv1_inference.sh', jobfile_hpc)

    # inference command terminal (nnUNetv1)
    inference_command = f'ssh jaime.barrancohernandez@chacha "sbatch {jobfile_hpc}"'
    os.system(inference_command)
    
    # copy output folder from hpc
    copy_folder_hpc(output_hpc, output)
    
    # Copy logs
    copy_folder(LOGS_FOLDER, os.path.join(output, 'logs'))  # needed for app.log

    return 'Inference finished!!'
