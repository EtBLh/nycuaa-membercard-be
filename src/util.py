import os
import shutil
import base64
import uuid
import smtplib
from mysql.connector import Error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.application import MIMEApplication
from email import encoders
from email.message import EmailMessage
from src import api
from src import db

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

def fetch_member_by_namegovid(govid, name):
    try:
        connection = db.pool.get_connection()
        if connection.is_connected():
            db_info = connection.get_server_info()
            print(f'[+] connected to MySQL Server version {db_info}')
            
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM member_id WHERE govid = %s AND name = %s;", (govid, name))
            
            if record := cursor.fetchone():
                # if qrcode does not exist, update DB
                if qrcode := record[7] is None :
                    uid = str(uuid.uuid4())
                    cursor.execute("UPDATE member_id SET qrcode = %s WHERE govid = %s AND name = %s;", (new_qrcode, govid, name))
                    connection.commit()
                    record[7] = uid
                    print(f'[+] db: member {name} does not have qrcode, created qrcode={qrcode} for member')

                cursor.close()
                connection.close()
                return record, True
            else:
                print(f'[-] db: no matching data found(govid={govid}, name={name})')
                return None, True
    except Error as e:
        print(f'[-] db error: {e}')
        return None, False

def fetch_member_by_qrcode(qrcode):
    try:
        connection = db.pool.get_connection()
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM member_id WHERE qrcode = %s;", [qrcode])
            
            if record := cursor.fetchone():
                cursor.close()
                connection.close()
                return record, True
            else:
                print(f'[-] db: no matching data found(qrcode={qrcode})')
                return None, True
    except Error as e:
        print(f'[-] db error: {e}')
        return None, False

# TODO: finish this function
def checkin_member_by_id(id):
    try:
        connection = db.pool.get_connection()
        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT * FROM member_id WHERE qrcode = %s;", [qrcode])
            
            if record := cursor.fetchone():
                cursor.close()
                connection.close()
                return record, True
            else:
                print(f'[-] db: no matching data found(qrcode={qrcode})')
                return None, True
    except Error as e:
        print(f'[-] db error: {e}')
        return None, False

def send_email_with_attachment( subject, to_email, attachment_path ):

    from_email=os.getenv('email')
    from_email_password=os.getenv('email_pw')

    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    
    with open('output.html', 'r', encoding='utf-8') as file:
        html_content = file.read()

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
        mail_server = smtplib.SMTP('smtp.gmail.com', 587)
        mail_server.starttls()
        mail_server.login(from_email, from_email_password)
        mail_server.sendmail(from_email, to_email, msg.as_string())
        print(f'Email sent to {to_email}')
    except Exception as e:
        print(f'Failed to send email: {e}')