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
    SECRET_KEY = os.getenv('SECRET_KEY', 'ALongRandomlyGeneratedString')
    
    # Auth0
    AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID', 'YOUR_AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET', 'YOUR_AUTH0_CLIENT_SECRET')
    AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN', 'dev-efo7i5wwqsmfsqvt.eu.auth0.com')
    AUTH0_AUDIENCE = os.getenv('AUTH0_AUDIENCE', 'https://dev-efo7i5wwqsmfsqvt.eu.auth0.com/api/v2/')
    AUTH0_CALLBACK_URL = os.getenv('AUTH0_CALLBACK_URL', 'http://localhost:5000/callback')

    # Mail config
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
