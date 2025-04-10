from flask import Flask,  request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from mysql.connector import Error
from io import BytesIO
import random
import string
import uuid
import os
import re
from threading import Thread
from datetime import datetime
from PIL import Image, ImageFile, ExifTags

# -----------------env var-----------------
from dotenv import load_dotenv
load_dotenv(override=True)
# -----------------------------------------

from src import util
from src import pkpass
from src import db

ImageFile.LOAD_TRUNCATED_IMAGES = True

# flask app
app = Flask(__name__)
CORS(app)

# login with govid and name
@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    name = data["name"]
    govid = data["govid"]

    if not name or not govid:
        return jsonify({"error": "Name and govid are required"}), 400

    session = db.session_local()

    try:
        # Retrieve the user based on name and govid
        user = session.query(db.Member).filter_by(name=name, govid=govid).first()

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Generate a 6-digit OTP code
        code = ''.join(random.choices(string.digits, k=6))

        # Update user's OTP code in the database
        user.otpcode = code
        session.commit()

        # Send the OTP code via email
        util.send_2fa_email("【陽明交大校友總會】會員證系統—驗證碼", user.email, code)

        # Censor the account name 
        censored_email = re.sub(r'^([^@]{3})([^@]*)@', lambda m: m.group(1) + '*' * len(m.group(2)) + '@', user.email)

        return jsonify({"message": "otp code sent", "email": censored_email}), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

# verify with otp sent to email to complete login
@app.route("/api/otp_verify", methods=["POST"])
def otp_verify():
    data = request.get_json()
    code = data.get("code")
    name = data.get("name")
    govid = data.get("govid")

    if not code or not name or not govid:
        return jsonify({"error": "Code, name, and govid are required"}), 400

    session = db.session_local()
    try:
        # Retrieve the member based on 2FA code, name, and govid
        member = session.query(db.Member).filter_by(otpcode=code, name=name, govid=govid).first()

        if not member:
            return jsonify({"error": "Invalid 2FA code"}), 401

        # Generate a 32-character token
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

        # Update member's token in the database
        member.token = token
        member.otpcode = ''
        session.commit()

        return jsonify({
            "token": token,
            'id': member.id,
            'name': member.name,
            'email': member.email,
            'govid': member.govid,
        }), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

# get member data
@app.route('/api/member', methods=['GET'])
def get_member_by_token():
    session = db.session_local()
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header:
            token = auth_header.split()[1]
            member = session.query(db.Member).filter_by(token=token).first()
            if member:
                permit = session.query(db.MemberCardIssuePermit).filter_by(member_id=member.id, year=datetime.now().year).first()
                if permit:
                    return jsonify({
                        'id': member.id,
                        'name': member.name,
                        'email': member.email,
                        'govid': member.govid,
                        'permit': True
                    }), 200
                else:
                    return jsonify({
                        'id': member.id,
                        'name': member.name,
                        'email': member.email,
                        'govid': member.govid,
                        'permit': False
                    }), 200
            else:
                return jsonify({'message': 'Member not found'}), 404
        else:
            return jsonify({'message': 'Authorization header missing'}), 400
    except Exception as e:
        session.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        session.close()


# check is token ok
@app.route('/api/member/check_token', methods=['POST'])
def check_token():
    auth_header = request.headers.get('Authorization')
    token = ''
    if auth_header:
        token = auth_header.split()[1]  # Extracts the token

    if not token:
        return jsonify({'valid': False, 'error': 'Token is required'}), 400

    try:
        session = db.session_local()
        member = session.query(db.Member).filter_by(token=token).first()

        if member:
            return jsonify({'valid': True }), 200
        else:
            return jsonify({'valid': False }), 401
    except Exception as e:
        return jsonify({'message': f'DB error: {str(e)}'}), 500
    finally:
        session.close()

# write a check in record with qrcode on membercard
@app.route('/api/member/check-in/<qrcode>', methods=['POST'])
def qrcode_check_in(qrcode):
    session = db.session_local()
    try:
        # Retrieve member data based on the QR code
        member_data = session.query(db.Member).filter(qrcode=qrcode).first()
        if member_data:
            # Create a new check-in record
            check_in_record = CheckInRecord(
                member_id=member_data.token,
                datetime=datetime.utcnow()
            )
            session.add(check_in_record)
            session.commit()
            return jsonify({'name': member_data.name, 'message': 'Check-in successful'}), 200
        else:
            return jsonify({'message': 'No member found with the provided QR code'}), 404
    except Exception as e:
        session.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        session.close()

# upload icon
@app.route('/api/member/icon', methods=['PUT'])
def upload_member_icon():
    # Ensure the request contains a file and an Authorization header
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    if 'Authorization' not in request.headers:
        return jsonify({'error': 'Authorization header is missing'}), 401

    file = request.files['file']
    auth_header = request.headers['Authorization']
    token = auth_header.split(" ")[1] if len(auth_header.split(" ")) > 1 else None

    if not token:
        return jsonify({'error': 'Bearer token is missing'}), 401

    # Initialize database session
    session = db.session_local()
    try:
        # Query the Member based on the provided token
        member = session.query(db.Member).filter_by(token=token).first()

        if not member:
            return jsonify({'error': 'Invalid token'}), 401

        # Check if the file is a valid image by trying to open it
        try:
            img = Image.open(file)
            img.verify()  # Verify the image integrity
        except (IOError, SyntaxError) as e:
            return jsonify({'error': 'Invalid image file'}), 400

        # Secure the filename and save the file as PNG
        filename = f"{member.govid}.png"  # Save as .png
        filepath = os.path.join(os.getcwd(), os.getenv('icons_path'), filename)

        # Convert and save the image as PNG
        img = Image.open(file)

        # Correct the image orientation if necessary
        try:
            # Check if image has EXIF data
            exif = img._getexif()
            if exif is not None:
                # Iterate through EXIF tags and look for orientation tag
                for tag, value in exif.items():
                    if tag in ExifTags.TAGS and ExifTags.TAGS[tag] == 'Orientation':
                        if value == 3:
                            img = img.rotate(180, expand=True)
                        elif value == 6:
                            img = img.rotate(270, expand=True)
                        elif value == 8:
                            img = img.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            pass  # No EXIF data or invalid EXIF tag, just continue
        
        img.thumbnail((1024,1024)) # Resize img to save disk space
        img.save(filepath, 'PNG')  # Save as PNG format

        return jsonify({'message': 'Icon uploaded successfully'}), 200
    except Exception as e:
        print(f'error {str(e)}')
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    finally:
        session.close()

# get user icon
@app.route('/api/member/icon', methods=['GET'])
def get_member_icon():

    # Extract the Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization token is missing or invalid'}), 401

    # Extract the token
    token = auth_header.split(' ')[1]

    # Authenticate the user based on the token
    session = db.session_local()
    try:
        member = session.query(db.Member).filter_by(token=token).first()
        if not member:
            return jsonify({'error': 'Invalid token'}), 401

        icon_directory = os.path.join(os.getcwd(), os.getenv('icons_path'))
        icon_filename = util.get_icon_name_by_govid(icon_directory, member.govid)

        if not icon_filename:
            return jsonify({'error': 'Icon not found'}), 404

        # Serve the icon file
        return send_from_directory(icon_directory, icon_filename)
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    finally:
        session.close()

@app.route('/api/member/pass', methods=['POST'])
def create_member_pass():
    # Extract the Authorization header
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization token is missing or invalid'}), 401

    # Extract the token
    token = auth_header.split(' ')[1]

    # Authenticate the user based on the token
    session = db.session_local()

    try:
        member = session.query(db.Member).filter_by(token=token).first()

        if not member:
            return jsonify({'error': 'token invalid'}), 400
        
        permit = session.query(db.MemberCardIssuePermit).filter_by(member_id=member.id, year=datetime.now().year).first()
        if not permit:
            return jsonify({'error': 'no permit found'}), 403

        if not member.qrcode:
            member.qrcode = uuid.uuid4()
            session.commit()

        ok, message = pkpass.newpass(member, permit)
        if not ok:
            if message == 'icon_missing':
                return jsonify({'error': 'missing field: icon'}), 400
            else:
                return jsonify({'error': 'error creating pass'}), 400
        
        dst = os.path.join(os.getcwd(), os.getenv('pkfiles_path'), member.qrcode+".pkpass")
        
        email_template_path = os.path.join(os.getcwd(), 'src', 'email_templates','output.html')
        Thread(target=util.send_email_with_attachment, args=("【陽明交大校友總會】2025年度會員證—寄發信", member.email, email_template_path, dst)).start()

        return jsonify({"status": "success"}), 200

    except Exception as e:
        print(f'error {str(e)}')
        return jsonify({'error': str(e)}), 500

# get user pass
@app.route('/api/download/member_pass.pkpass', methods=['GET'])
def get_member_pass():

    token = request.args.get('token')

    # Extract the Authorization header
    if not token:
        return jsonify({'error': 'Authorization token is missing or invalid'}), 401

    # Authenticate the user based on the token
    session = db.session_local()
    try:
        member = session.query(db.Member).filter_by(token=token).first()
        if not member:
            return jsonify({'error': 'Invalid token'}), 401

        directory = os.path.join(os.getcwd(), os.getenv('pkfiles_path'))
        filename = f'{member.qrcode}.pkpass'

        if not os.path.exists(os.path.join(directory, filename)):
            return jsonify({'error': 'pkpass file not found'}), 404

        return send_from_directory(directory, filename, mimetype='application/vnd.apple.pkpass', as_attachment=True)
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    finally:
        session.close()

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200
