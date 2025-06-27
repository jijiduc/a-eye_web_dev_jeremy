import os
import logging
from flask import Flask
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
from authlib.integrations.flask_client import OAuth

from config import (
    Config,
    LOGS_FOLDER,
    UPLOAD_FOLDER,
    DOWNLOAD_FOLDER,
    OUTPUT_ZIP,
    DATA_FOLDER,
    ALLOWED_EXTENSIONS
)

mail = Mail()
oauth = OAuth()

def create_app():
    load_dotenv()

    app = Flask(__name__, static_folder="static")
    app.config.from_object(Config)
    # Inject extra config values
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER
    app.config['OUTPUT_ZIP'] = OUTPUT_ZIP
    app.config['DATA_FOLDER'] = DATA_FOLDER
    app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS
    app.secret_key = os.getenv('APP_SECRET_KEY', 'ALongRandomlyGeneratedString')
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    # Logging
    logging.basicConfig(
        filename=f'{LOGS_FOLDER}/app.log',
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)s %(name)s %(message)s'
    )

    mail.init_app(app)
    oauth.init_app(app)

    # Register Auth0
    oauth.register(
        'auth0',
        client_id=app.config['AUTH0_CLIENT_ID'],
        client_secret=app.config['AUTH0_CLIENT_SECRET'],
        api_base_url=f"https://{app.config['AUTH0_DOMAIN']}",
        access_token_url=f"https://{app.config['AUTH0_DOMAIN']}/oauth/token",
        authorize_url=f"https://{app.config['AUTH0_DOMAIN']}/authorize",
        client_kwargs={'scope': 'openid profile email'},
        server_metadata_url=f"https://{app.config['AUTH0_DOMAIN']}/.well-known/openid-configuration"
    )

    # Register routes
    from routes import bp as routes_bp
    app.register_blueprint(routes_bp)

    return app
