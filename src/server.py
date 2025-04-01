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
from src import util
from src import pkpass
from mysql.connector import pooling

# flask app
app = Flask(__name__)
# mysql connection pool
dbpool = pooling.MySQLConnectionPool(
    pool_name="membercard_db_pool",
    pool_size=5,
    host=os.getenv('db_host'),
    user=os.getenv('db_user'),
    password=os.getenv('db_pw'),
    database=os.getenv('db_database')
)

@app.route('/api/login', methods=['POST'])
def login():
    pass

@app.route('/api/logout', methods=['POST'])
def logout():
    pass

@app.route('/api/user_icon', methods=['GET'])
def get_user_icon():
    pass

@app.route('/api/newpass', methods=['POST'])
def newpass():
    name = request.args.get('name')
    govid = request.args.get('govid')
    try:
        form_data = request.get_json()
    except Exception as e:
        return jsonify({'error': 'Invalid JSON format'}), 400

    try:
        record = util.fetch_user_by_nameid(govid, name)
    except Exception as e:
        return jsonify({'error': 'No user found'}), 400

    if not record:
        return jsonify({'error': 'No user found'}), 400

    current_dir = os.getcwd()
    source_folder = os.path.join(current_dir, 'template')
    destination_folder = os.path.join(current_dir, govid)
    copy_folder(source_folder, destination_folder)

    if 'icon' in form_data:
        file_data = form_data.pop('file')

        # Decode the Base64 string
        file_bytes = base64.b64decode(file_data)
        
        # Convert the file to an image and then to PNG
        image = Image.open(BytesIO(file_bytes))
        file_path = os.path.join(os.getenv('icons_path'), govid + '.png')
        image.save(file_path, 'PNG')

        file_path = os.path.join(destination_folder, "thumbnail@2x.png")
        image.save(file_path, 'PNG')

        file_path = os.path.join(destination_folder, "thumbnail.png")
        image.save(file_path, 'PNG')
    else:
        delete_folder(destination_folder)
        return jsonify({'error': 'missing field: icon'}), 400
    pkpass.newpass(rt[1],rt[7],rt[2],rt[0])
    
    dst = os.path.join("/var/www/pass_files", rt[1]+".pkpass")
    send_email_with_attachment("【陽明交大校友總會】2025年度會員證—寄發信", rt[0][5], dst)
    return "success"
    
@app.route('/api/upload_icon', methods=['POST'])
def upload_icon():
    name = request.args.get('name')
    govid = request.args.get('govid')
    try:
        form_data = request.get_json()
    except Exception as e:
        return jsonify({'error': 'Invalid JSON format'}), 400

    try:
        record = util.fetch_user_by_nameid(govid, name)
    except Exception as e:
        return jsonify({'error': 'No user found'}), 400

    if not record:
        return jsonify({'error': 'No user found'}), 400

    current_dir = os.getcwd()
    source_folder = os.path.join(current_dir, 'template')
    destination_folder = os.path.join(current_dir, govid)
    copy_folder(source_folder, destination_folder)

    if 'icon' in form_data:
        file_data = form_data.pop('file')

        # Decode the Base64 string
        file_bytes = base64.b64decode(file_data)
        
        # Convert the file to an image and then to PNG
        image = Image.open(BytesIO(file_bytes))
        file_path = os.path.join(os.getenv('icons_path'), govid + '.png')
        image.save(file_path, 'PNG')

        file_path = os.path.join(destination_folder, "thumbnail@2x.png")
        image.save(file_path, 'PNG')

        file_path = os.path.join(destination_folder, "thumbnail.png")
        image.save(file_path, 'PNG')
    else:
        delete_folder(destination_folder)
        return jsonify({'error': 'missing field: icon'}), 400

    return "success"

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200
