import os
from datetime import datetime
from utils import *
from config import LOGS_FOLDER, DOWNLOAD_FOLDER

# ----------------------------------------------------------------------------------------------
# MAIN FUNCTION

def getSegmentation(output=None, user_email=None):
    ''' Main function: performs inference on input folder and saves output in output folder. '''

    # paths
    output = DOWNLOAD_FOLDER
    output_hpc = 'jaime.barrancohernandez@chacha:/home/jaime.barrancohernandez/results/nnunet'
    template = './jobfiles/nnunet_inference_template.sh'
    jobfile = './jobfiles/nnunet_inference.sh'
    jobfile_hpc = '/home/jaime.barrancohernandez/shared_datasets/nnunet/nnunet_inference.sh'
    
    # We would need this for copying the resulting files from the HPC to the local machine
    # Make the email safe for paths
    safe_email = re.sub(r'[@.]', '_', user_email)
    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # modify jobfile
    modify_jobfile(template, user_email, timestamp, jobfile)
        
    # copy jobfile to hpc
    copy_file_hpc(jobfile, 'jaime.barrancohernandez@chacha:/home/jaime.barrancohernandez/shared_datasets/nnunet/')

    # inference command terminal (nnUNet)
    inference_command = f'ssh jaime.barrancohernandez@chacha "sbatch {jobfile_hpc}"'
    os.system(inference_command)
    
    # copy output folder from hpc
    copy_folder_hpc(f'{output_hpc}/{safe_email}_{timestamp}', output)
    
    # Copy logs
    copy_folder(LOGS_FOLDER, os.path.join(output, 'logs'))  # needed for app.log

    return '\nInference finished!!'
