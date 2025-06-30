import os
from dotenv import load_dotenv

load_dotenv()  # load env variables once

# Paths
UPLOAD_FOLDER = "./static/upload"
DOWNLOAD_FOLDER = "/app/nnUNet/nnUNet_inference/output"
OUTPUT_ZIP = "/app/nnUNet/nnUNet_inference/output.zip"
DATA_FOLDER = "/app/filer01"
LOGS_FOLDER = "./logs"
ALLOWED_EXTENSIONS = {'gz', 'zip', '7z'}

    
class Config:
    # Flask secret key
    SECRET_KEY = os.getenv('SECRET_KEY')
    
    # Auth0
    AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET')
    AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN')
    AUTH0_AUDIENCE = os.getenv('AUTH0_AUDIENCE')
    AUTH0_CALLBACK_URL = os.getenv('AUTH0_CALLBACK_URL')

    # Mail config
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS')
    MAIL_USE_SSL = os.getenv('MAIL_USE_SSL')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
