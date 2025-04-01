from src import server
from src import util
import os
from dotenv import load_dotenv

if __name__ == '__main__':

    load_dotenv()

    upload_folder_path_path = 'uploads'
    if not os.path.exists(upload_folder_path_path):
        os.makedirs(upload_folder_path_path)

    # Define the paths to the certificate and key files
    # cert_file = '/etc/letsencrypt/live/nycuaa.org/fullchain.pem'
    # key_file = '/etc/letsencrypt/live/nycuaa.org/privkey.pem'
    rt = util.fetch_user_by_nameid("membership.ct4ismqeal59.ap-northeast-1.rds.amazonaws.com","member", "admin", "nycuaa123x", "D123002248","王吉磊")
    # Run the Flask app with SSL

    # app.run(ssl_context=(cert_file, key_file), host='0.0.0.0', port=5000)
    server.app.run( host='0.0.0.0', port=5000)
