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
from email.message import EmailMessage

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
                
    except Error as e:
        print(f'Error: {e}')
        return []

def send_email_with_attachment( to_email, attachment_path):
    # Create the email message
    from_email="member_card@nycuaa.org"
    from_email_password="qbak zcwk bkko zydp"
    msg = MIMEMultipart('mixed')
    msg['Subject'] = "【陽明交大校友總會】2025年度會員證—寄發信"
    msg['From'] = from_email
    msg['To'] = to_email
    with open('updatepass.html', 'r', encoding='utf-8') as file:
        html_content = file.read()
    # print(html_content)
    html_part = MIMEText(html_content, 'html')
    msg.attach(html_part)
    if attachment_path:
        print(f"attachment(card file): {attachment_path}")
        file_name = os.path.basename(attachment_path)
        with open(attachment_path, 'rb') as attachment_file:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment_file.read())

        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            f'attachment; filename={file_name}',
        )
        msg.attach(part)
        # Connect to the SMTP server and send the email
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(from_email, from_email_password)
        server.sendmail(from_email, to_email, msg.as_string())
        print(f'Email sent to {to_email}')
    except Exception as e:
        print(f'Failed to send email: {e}')


if __name__ == '__main__':
    # Define the paths to the certificate and key files
    cert_file = '/etc/letsencrypt/live/nycuaa.org/fullchain.pem'
    key_file = '/etc/letsencrypt/live/nycuaa.org/privkey.pem'
    send_email_with_attachment("jim1010336@gmail.com","/var/www/pass_files/a49bbd7e-9113-417c-b690-cd2bdba4ca92.pkpass", "/home/ubuntu/membercard/invoice/1.pdf")
