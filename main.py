import os
import subprocess
from datetime import datetime
from utils import modify_jobfile, print_and_log, copy_file_to_hpc, copy_files_from_hpc, user_reference_rmtree, move_file, copy_folder
from config import JOBFILE_HPC, SSH_USER, LOGS_FOLDER, JOBFILE_TEMPLATE, OUTPUT_HPC
from models import UserPaths

# ----------------------------------------------------------------------------------------------
# MAIN FUNCTION

def getSegmentation(user_email: str, paths: UserPaths) -> str:
    """Main function : performs inference on input folder and saves output in output folder

    Args:
        user_email (str): user's email address
        paths (UserPaths): the generated paths based on the user's adress

    Returns:
        str: a message to announce segmentation done
    """
    # We would need this for copying the resulting files from the HPC to the local machine
    # Make the email safe for paths
    safe_email = user_email.replace("@", "_at_").replace(".", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    jobfile     = paths.jobfile
    jobfile_hpc = f"{os.path.dirname(JOBFILE_HPC)}/nnunet_inference_{safe_email}.sh"

    modify_jobfile(JOBFILE_TEMPLATE, user_email, timestamp, jobfile, paths.hpc_input)
    copy_file_to_hpc(jobfile, os.path.dirname(jobfile_hpc))
    # inference command terminal (nnUNet)
    inference_command = f'ssh {SSH_USER} "sbatch --wait --partition=Dance --account=mattech --qos=normal {jobfile_hpc}"'
    print_and_log("[A-eye] Submitted batch job to HPC...", 'info', LOGS_FOLDER)
    subprocess.run(inference_command, shell=True, check=True)

    copy_files_from_hpc(f'{OUTPUT_HPC}/{safe_email}_{timestamp}', paths.download)
    # Logs handling
    output_logs = paths.download / 'logs'
    if output_logs.exists():
        user_reference_rmtree(output_logs)
    output_logs.mkdir(parents=True, exist_ok=True)
    move_file(str(paths.download / '*.err'), output_logs)
    move_file(str(paths.download / '*.out'), output_logs)
    
    copy_folder(LOGS_FOLDER, output_logs)

    return '\nInference finished!!'
