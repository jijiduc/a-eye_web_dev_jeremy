import os, shutil

LOGS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../logs/')

def copy_file(source, destination):
    if not os.path.exists(destination):
        os.mkdir(destination)
    shutil.copy(source, destination)

args_out = '/home/jaimebarranco/Desktop/test_inference/output' # origin output folder

copy_file(f'{LOGS_FOLDER}app.log', args_out)