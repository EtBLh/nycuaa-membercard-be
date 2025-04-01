#! ./bin/python3.12

from flask import Flask,  request, jsonify
import hashlib
import json
import os
import subprocess
import shutil
from PIL import Image
from io import BytesIO
import mysql.connector
from mysql.connector import Error
import base64
import uuid
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
from test import send_email_with_attachment

cursor = ""
def copy_folder(src, dest):
    # Ensure the source directory exists
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source directory '{src}' does not exist.")
    
    try:
        shutil.copytree(src, dest)
        print(f"Folder '{src}' successfully copied to '{dest}'")
    except Exception as e:
        print(f"Error occurred while copying folder: {e}")

def delete_folder(folder_path):
    # Ensure the directory exists
    if not os.path.exists(folder_path):
        print(f"Directory '{folder_path}' does not exist.")
        return
    
    # Use shutil.rmtree to delete the directory
    try:
        shutil.rmtree(folder_path)
        print(f"Folder '{folder_path}' successfully deleted.")
    except Exception as e:
        print(f"Error occurred while deleting folder: {e}")

def move_file(src, dest):
    try:
        shutil.move(src, dest)
        print(f"File '{src}' successfully moved to '{dest}'")
    except Exception as e:
        print(f"Error occurred while moving file: {e}")

def connect_to_mysql(host, database, user, password, govid, name):
    try:
        # Connect to the MySQL database
        connection = mysql.connector.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        rt = []
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f'Connected to MySQL Server version {db_info}')
            
            cursor = connection.cursor()
            print(f"SELECT * from member_id where govid=\"{govid}\" and name=\"{name}\";")
            cursor.execute(f"SELECT * from member_id where govid=\"{govid}\" and name=\"{name}\";")
            record = cursor.fetchone()
            print(record)
            rt.append(record)
            cursor.execute(f"SELECT qr from qrcode where id=\"{record[0]}\";")
            rows = cursor.fetchall()
            if(len(rows) == 0):
                uid = str(uuid.uuid4())
                # print(f"INSERT INTO qrcode (id,qr) values (\"{record[0]}\", \"{uid}\");")
                cursor.execute(f"INSERT INTO qrcode (id,qr) values (\"{record[0]}\", \"{uid}\");")
                connection.commit()
                rt.append(uid)
            else:
                rt.append(rows[0][0])
            cursor.close()
            connection.close()
            return rt
            # cursor.execute('SELECT DATABASE();')
            # record = cursor.fetchone()
            # print(f'Connected to database: {record}')
            
            # # Example query
            # cursor.execute('SELECT * FROM your_table_name LIMIT 5;')
            # rows = cursor.fetchall()
            # for row in rows:
            #     print(row)
                
    except Error as e:
        print(f'Error: {e}')
        return []


app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
def generate_manifest(pass_directory):
    manifest = {}
    for root, _, files in os.walk(pass_directory):
        for file in files:
            if file not in ["manifest.json", "signature"]:
                file_path = os.path.join(root, file)
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    sha1_hash = hashlib.sha1(file_data).hexdigest()
                    manifest[file] = sha1_hash
    return manifest

def save_manifest(manifest, output_file):
    with open(output_file, 'w') as f:
        json.dump(manifest, f, indent=4)

def sign_manifest(pass_directory, wwdr_cert, signer_cert, signer_key):
    manifest_path = os.path.join(pass_directory, 'manifest.json')
    signature_path = os.path.join(pass_directory, 'signature')
    command = [
        'openssl', 'smime', '-binary', '-sign', '-certfile', wwdr_cert,
        '-signer', signer_cert, '-inkey', signer_key, '-in', manifest_path,
        '-out', signature_path, '-outform', 'DER'
    ]
    subprocess.check_call(command)

def create_pkpass(pass_directory, output_file):
    shutil.make_archive(output_file, 'zip', pass_directory)
    os.rename(output_file + '.zip', output_file + '.pkpass')


# @app.route('/api/newpass')
def newpass(name,qrcode,dir,govid,id):
    file_path = os.path.join(dir, "pass.json")
    with open(file_path, 'r') as file:
        data = json.load(file)
    data['serialNumber'] = govid
    data['webServiceURL'] = "https://nycuaa.org/passes/"
    data['authenticationToken'] = qrcode
    data['barcode']['message'] = qrcode
    data['generic']['primaryFields'][0]['value'] = name
    data['generic']['secondaryFields'][0]['value'] = "2024"
    if (id<2404452):
        data['generic']['auxiliaryFields'][0]['value'] = "普通會員（創始會員）"
    else:
        data['generic']['auxiliaryFields'][0]['value'] = "普通會員"
    # print(data)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
    pass_directory = dir
    wwdr_cert = "/home/ubuntu/membercard/WWDR.pem"
    signer_cert = "/home/ubuntu/membercard/signerCert.pem"
    signer_key = "/home/ubuntu/membercard/signerKey.pem"
    output_file = qrcode

    # Generate the manifest
    manifest = generate_manifest(pass_directory)
    save_manifest(manifest, os.path.join(pass_directory, "manifest.json"))
    print("Manifest generated successfully.")

    # Sign the manifest
    sign_manifest(pass_directory, wwdr_cert, signer_cert, signer_key)
    print("Manifest signed successfully.")

    # Create the .pkpass file
    create_pkpass(pass_directory, output_file)
    print(f"{output_file}.pkpass created successfully.")
    current_dir = os.getcwd()
    src = os.path.join(current_dir, output_file+".pkpass")
    dst = os.path.join("/var/www/pass_files", output_file+".pkpass")
    move_file(src,dst)
    return "success"

@app.route('/api/upload', methods=['POST'])
def upload_file():
    name = request.args.get('name')
    id = request.args.get('id')
    try:
        rt = connect_to_mysql("membership.ct4ismqeal59.ap-northeast-1.rds.amazonaws.com","member", "admin", "nycuaa123x", id, name)
    except Exception as e:
        return jsonify({'error': 'No user found'}), 400
    if (len(rt)==0 ):
        return jsonify({'error': 'No user found'}), 400
    try:
        form_data = request.get_json()
    except Exception as e:
        return jsonify({'error': 'Invalid JSON format'}), 400
    current_dir = os.getcwd()
    source_folder = os.path.join(current_dir, 'template')
    destination_folder = os.path.join(current_dir, id)
    copy_folder(source_folder, destination_folder)
    if 'file' in form_data and 'fileName' in form_data:
        file_data = form_data.pop('file')
        original_file_name = form_data.pop('fileName')

        # Decode the Base64 string
        file_bytes = base64.b64decode(file_data)
        
        # Convert the file to an image and then to PNG
        image = Image.open(BytesIO(file_bytes))
        png_file_name = id + '.png'
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], png_file_name)
        
        # Save the image as PNG
        image.save(file_path, 'PNG')
        file_path = os.path.join(destination_folder, "thumbnail@2x.png")
        image.save(file_path, 'PNG')
        file_path = os.path.join(destination_folder, "thumbnail.png")
        image.save(file_path, 'PNG')
    else:
        delete_folder(destination_folder)
        return jsonify({'error': 'File data missing in the request'}), 400
    newpass(rt[0][1],rt[1],destination_folder,rt[0][2],rt[0][0])
    id = int(rt[0][0])
    id = id-2400000
    id = id - id%10
    id = int(id /10)
    if (id>444):
        id = id - 1
    print(id)
    dst = os.path.join("/var/www/pass_files", rt[1]+".pkpass")
    send_email_with_attachment(rt[0][5],dst)
    return "success"

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Define the paths to the certificate and key files
    # cert_file = '/etc/letsencrypt/live/nycuaa.org/fullchain.pem'
    # key_file = '/etc/letsencrypt/live/nycuaa.org/privkey.pem'
    rt = connect_to_mysql("membership.ct4ismqeal59.ap-northeast-1.rds.amazonaws.com","member", "admin", "nycuaa123x", "D123002248","王吉磊")
    print(rt)
    # Run the Flask app with SSL
    # app.run(ssl_context=(cert_file, key_file), host='0.0.0.0', port=5000)
    app.run( host='0.0.0.0', port=5000)
