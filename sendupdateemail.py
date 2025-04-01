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

def send_email_with_attachment( to_email, attachment_path):
    # Create the email message
    from_email="member_card@nycuaa.org"
    from_email_password="mipnew-4deFvu-daxwub"
    msg = MIMEMultipart('mixed')
    msg['Subject'] = "【陽明交大校友總會】2025年度電子會員證寄發通知"
    msg['From'] = from_email
    msg['To'] = to_email
    with open('output.html', 'r', encoding='utf-8') as file:
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
