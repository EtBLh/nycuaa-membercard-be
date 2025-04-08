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
from flask import render_template
from jinja2 import Environment, FileSystemLoader

from dotenv import load_dotenv
load_dotenv()

def copy_folder(src: str, dest: str) -> None:
    # Ensure the source directory exists
    if not os.path.exists(src):
        raise FileNotFoundError(f"Source directory '{src}' does not exist.")
    
    try:
        shutil.copytree(src, dest)
        print(f"Folder '{src}' successfully copied to '{dest}'")
    except Exception as e:
        print(f"Error occurred while copying folder: {e}")

def delete_folder(folder_path: str) -> None:
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

def move_file(src: str, dest: str) -> None:
    try:
        shutil.move(src, dest)
        print(f"File '{src}' successfully moved to '{dest}'")
    except Exception as e:
        print(f"Error occurred while moving file: {e}")

def send_email_with_attachment( subject: str, to_email: str, template_path: str, attachment_path: str ) -> None:

    from_email=os.getenv('email')
    from_email_password=os.getenv('email_pw')

    msg = MIMEMultipart('mixed')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email
    
    with open(template_path, 'r', encoding='utf-8') as file:
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

def send_2fa_email(subject: str, to_email: str, code: str) -> None:
    from_email = os.getenv('email')
    from_email_password = os.getenv('email_pw')

    # 2fa content
    template_dir = os.path.join(os.getcwd(), "src", "email_templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("2fa.html")
    body = template.render(code=code)

    msg = MIMEText(body, 'html')
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to_email

    try:
        mail_server = smtplib.SMTP('smtp.gmail.com', 587)
        mail_server.starttls()
        mail_server.login(from_email, from_email_password)
        mail_server.sendmail(from_email, to_email, msg.as_string())
        mail_server.quit()
        print(f'2FA email sent to {to_email}')
    except Exception as e:
        print(f'Failed to send 2FA email: {e}')

def is_icon_ext_allowed(filename: str) -> bool:
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_icon_name_by_govid(icon_directory: str, govid: str) -> str|None:
    icon_filename = None
    for ext in ['png', 'jpg', 'jpeg', 'gif']:
        potential_filename = f"{govid}.{ext}"
        if os.path.exists(os.path.join(icon_directory, potential_filename)):
            return potential_filename
    return None

def pick(obj, *attrs):
    return [getattr(obj, attr) for attr in attrs]
