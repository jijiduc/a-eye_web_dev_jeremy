import os
from utils import *
from config import LOGS_FOLDER, UPLOAD_FOLDER, DOWNLOAD_FOLDER

# ----------------------------------------------------------------------------------------------
# MAIN FUNCTION

def getSegmentation(input=None, output=None, user_email=None):
    ''' Main function: performs inference on input folder and saves output in output folder. '''

    # paths
    input = UPLOAD_FOLDER
    output = DOWNLOAD_FOLDER
    input_hpc = 'jaime.barrancohernandez@chacha:/home/jaime.barrancohernandez/shared_datasets/nnunetv1/nnUNet/nnUNet_inference/input'
    output_hpc = 'jaime.barrancohernandez@chacha:/home/jaime.barrancohernandez/results/nnunetv1'
    jobfile = 'jobfiles/nnunetv1_inference.sh'
    jobfile_hpc = 'jaime.barrancohernandez@chacha:/home/jaime.barrancohernandez/shared_datasets/nnunetv1/nnunetv1_inference.sh'

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

    return '\nInference finished!!'
