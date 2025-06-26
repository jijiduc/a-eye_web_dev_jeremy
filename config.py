import os

LOGS_FOLDER = "./logs"

class Config:
    AUTH0_CLIENT_ID = os.getenv('AUTH0_CLIENT_ID', 'YOUR_AUTH0_CLIENT_ID')
    AUTH0_CLIENT_SECRET = os.getenv('AUTH0_CLIENT_SECRET', 'YOUR_AUTH0_CLIENT_SECRET')
    AUTH0_DOMAIN = os.getenv('AUTH0_DOMAIN', 'dev-efo7i5wwqsmfsqvt.eu.auth0.com')
    AUTH0_AUDIENCE = os.getenv('AUTH0_AUDIENCE', 'https://dev-efo7i5wwqsmfsqvt.eu.auth0.com/api/v2/')
    AUTH0_CALLBACK_URL = os.getenv('AUTH0_CALLBACK_URL', 'http://localhost:5000/callback')
    SECRET_KEY = os.getenv('SECRET_KEY', 'ALongRandomlyGeneratedString')