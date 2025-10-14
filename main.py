import os
from datetime import datetime
from utils import *
from config import *

# ----------------------------------------------------------------------------------------------
# MAIN FUNCTION

def getSegmentation(output=None, user_email=None):
    ''' Main function: performs inference on input folder and saves output in output folder. '''

    # paths
    output = DOWNLOAD_FOLDER
    output_hpc = OUTPUT_HPC
    template = JOBFILE_TEMPLATE
    jobfile = JOBFILE
    jobfile_hpc = JOBFILE_HPC
    
    # We would need this for copying the resulting files from the HPC to the local machine
    # Make the email safe for paths
    safe_email = re.sub(r'[@.]', '_', user_email)
    # Timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # modify jobfile
    modify_jobfile(template, user_email, timestamp, jobfile)
        
    # copy jobfile to hpc
    copy_file_to_hpc(jobfile, os.path.dirname(jobfile_hpc))

    # inference command terminal (nnUNet)
    inference_command = f'ssh {SSH_USER} "sbatch --wait {jobfile_hpc}"'
    print_and_log("[A-eye] Submitted batch job to HPC...", 'info', LOGS_FOLDER)
    os.system(inference_command)
    
    # copy output folder from hpc
    copy_files_from_hpc(f'{output_hpc}/{safe_email}_{timestamp}', output)
    move_file(f'{output}/*.err', os.path.join(output, 'logs'))  # move error files to logs folder
    move_file(f'{output}/*.out', os.path.join(output, 'logs'))  # move output files to logs folder
    
    # Copy logs
    copy_folder(LOGS_FOLDER, os.path.join(output, 'logs'))  # needed for app.log

    return '\nInference finished!!'
