#! python

# -----------------env var-----------------
from dotenv import load_dotenv
load_dotenv(override=True)
# -----------------------------------------

from src import api
from src import util
import os

if __name__ == '__main__':

    icons_path = os.getenv('icons_path')
    if not os.path.exists(icons_path):
        os.makedirs(icons_path)

    # Define the paths to the certificate and key files
    # cert_file = '/etc/letsencrypt/live/nycuaa.org/fullchain.pem'
    # key_file = '/etc/letsencrypt/live/nycuaa.org/privkey.pem'

    # app.run(ssl_context=(cert_file, key_file), host='0.0.0.0', port=5000)
    api.app.run( host='0.0.0.0', port=5000 )
