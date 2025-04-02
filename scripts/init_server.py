#! python

# -----------------env var-----------------
from dotenv import load_dotenv
load_dotenv(override=True)
# -----------------------------------------

from src import api
from src import util
import os

if __name__ == '__main__':

    uploads_path = os.getenv('uploads_path')
    if not os.path.exists(uploads_path):
        os.makedirs(uploads_path)

    # Define the paths to the certificate and key files
    # cert_file = '/etc/letsencrypt/live/nycuaa.org/fullchain.pem'
    # key_file = '/etc/letsencrypt/live/nycuaa.org/privkey.pem'
    record = util.fetch_member_by_namegovid("D123002248","王吉磊")

    # app.run(ssl_context=(cert_file, key_file), host='0.0.0.0', port=5000)
    api.app.run( host='0.0.0.0', port=5000 )
