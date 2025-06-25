from functools import wraps
import bcrypt
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
from pymysql import IntegrityError
from sqlalchemy import String, and_, cast, exists, or_
from werkzeug.utils import secure_filename
from mysql.connector import Error
from io import BytesIO
import random
import string
import uuid
import os
import re
from threading import Thread
from datetime import datetime, timedelta
import time 
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
CORS(app, origins="*")

# ---------------------- member api ----------------------

# member auth decorator, check if member token in Bearer Header, also put session, member, token in flask.g
def member_auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        session = db.session_local()
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid Authorization header'}), 401

            token = auth_header.split()[1]
            member = session.query(db.Member).filter_by(token=token).first()
            if not member:
                return jsonify({'error': 'Invalid or expired token'}), 401
            g.session = session
            g.member = member
            g.token = token
        except Exception as e:
            return jsonify({'error': 'Authentication failed', 'details': str(e)}), 401
        return f(*args, **kwargs)

    return wrapper

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
            return jsonify({"error": "Invalid 2FA code"}), 400

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
@member_auth_required
def get_member_by_token():
    member = getattr(g, 'member', None)
    session = getattr(g, 'session', None)
    try:
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
    except Exception as e:
        session.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        session.close()


# check is token ok
@app.route('/api/member/check_token', methods=['POST'])
@member_auth_required
def member_check_token():
    return jsonify({'valid': True }), 200

# upload icon
@app.route('/api/member/icon', methods=['PUT'])
@member_auth_required
def upload_member_icon():
    member = getattr(g, 'member', None)

    # Ensure the request contains a file and an Authorization header
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

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

# get user icon
@app.route('/api/member/icon', methods=['GET'])
@member_auth_required
def get_member_icon():
    member = getattr(g, 'member', None)

    icon_directory = os.path.join(os.getcwd(), os.getenv('icons_path'))
    icon_filename = util.get_icon_name_by_govid(icon_directory, member.govid)

    if not icon_filename:
        return jsonify({'error': 'Icon not found'}), 404

    # Serve the icon file
    return send_from_directory(icon_directory, icon_filename)

@app.route('/api/member/pass', methods=['POST'])
@member_auth_required
def create_member_pass():
    member = getattr(g, 'member', None)
    session = getattr(g, 'session', None)

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

# this supposed to be a public file url, where member can download the pass by <a href="/api/download/member_pass.pkpass">Download</a>
# and <a/> does not support adding http header, therefore this API entry is not using @member_auth_required but manully check the token in url param
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

# ---------------------- admin api ----------------------

# admin auth decorator, check if admin token in Bearer Header, also put session, member, token in flask.g
def admin_auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        session = db.session_local()
        try:
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Missing or invalid Authorization header'}), 401

            token = auth_header.split()[1]
            admin = session.query(db.Admin).filter_by(token=token).first()
            if not admin:
                return jsonify({'error': 'Invalid token'}), 401
            if bool(admin.token_expiry_time) and admin.token_expiry_time < int(time.time()):
                return jsonify({'error': 'expired token'}), 401
            
            # lengthen the time of admin.token_expiry time to now+60min
            admin.token_expiry_time = int(time.time()) + 60 * 60
            session.commit()

            g.session = session
            g.admin = admin
            g.token = token
        except Exception as e:
            return jsonify({'error': 'Authentication failed', 'details': str(e)}), 401
        return f(*args, **kwargs)

    return wrapper


# check is admin token ok
@app.route('/api/admin/check_token', methods=['POST'])
@admin_auth_required
def admin_check_token():
    return jsonify({'valid': True }), 200

@app.route('/api/admin/members', methods=['GET'])
@admin_auth_required
def get_members_by_admin():
    session = g.session
    try:
        page_size = int(request.args.get('pagesize', 10))
        page = int(request.args.get('page', 0))
        filter_status = request.args.get('status')
        filter_type = request.args.get('type')
        search_term = request.args.get('search', '').strip()
        current_year = datetime.now().year

        # Load file names from icon and card directories
        icon_dir = os.path.join(os.getcwd(), os.getenv('icons_path'))
        card_dir = os.path.join(os.getcwd(), os.getenv('passes_path'))
        
        existed_icon = set(os.listdir(icon_dir)) if os.path.exists(icon_dir) else set()
        existed_card = set(os.listdir(card_dir)) if os.path.exists(card_dir) else set()

        # Subquery for permit check
        permit_subq = session.query(db.MemberCardIssuePermit.member_id).filter_by(year=current_year).subquery()

        query = session.query(db.Member)

        # Apply filter
        if filter_status == 'paid':
            query = query.filter(db.Member.id.in_(permit_subq))
        elif filter_status == 'unpaid':
            query = query.filter(~db.Member.id.in_(permit_subq))

        if not filter_type == None:
            query = query.filter(db.Member.name == filter_type)
        
        # Apply search
        if search_term:
            like_term = f"%{search_term}%"
            query = query.filter(or_(
                db.Member.name.ilike(like_term),
                db.Member.govid.ilike(like_term),
                cast(db.Member.id, String).ilike(like_term)
            ))

        total = query.count()

        members = (
            query.offset(page * page_size)
                 .limit(page_size)
                 .all()
        )

        data = []
        for m in members:
            has_permit = False
            if filter_status != None:
                has_permit = filter_status == 'paid'
            else:
                has_permit = session.query(
                    exists()
                    .where(
                        db.MemberCardIssuePermit.member_id == m.id,
                    ).where(
                        db.MemberCardIssuePermit.year == current_year
                    )
                ).scalar()
            govid = m.govid or ""

            # Check if file named with govid exists
            icon_uploaded = any(govid == fname.split('.')[0] for fname in existed_icon)
            card_created = any(govid == fname for fname in existed_card)

            data.append({
                'id': m.id,
                'type': m.type,
                'name': m.name,
                'govid': m.govid,
                'email': m.email,
                'phone': m.phone,
                'birthday': m.birthday,
                'qrcode': m.qrcode,
                'permit': has_permit,
                'icon_uploaded': icon_uploaded,
                'card_created': card_created
            })

        return jsonify({
            'total': total,
            'page': page,
            'pagesize': page_size,
            'members': data
        }), 200

    except Exception as e:
        session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500
    finally:
        session.close()

@app.route('/api/admin/member/add', methods=['POST'])
@admin_auth_required
def add_member():
    data = request.get_json()
    required_fields = ['id', 'name', 'govid', 'email']

    # Accept both single object and array
    if isinstance(data, dict):
        members_data = [data]
    elif isinstance(data, list):
        members_data = data
    else:
        return jsonify({'error': 'Invalid input format'}), 400

    session = g.session
    results = []
    for member_data in members_data:
        # Check required fields
        if not all(field in member_data for field in required_fields):
            results.append({'id': member_data.get('id'), 'error': 'Missing required fields'})
            continue
        try:
            new_member = db.Member(
                id=member_data['id'],
                name=member_data.get('name'),
                govid=member_data['govid'],
                phone=member_data.get('phone'),
                birthday=member_data.get('birthday'),
                email=member_data['email'],
                type=member_data.get('type'),
            )
            session.add(new_member)
            session.flush()  # flush to catch IntegrityError per member
            results.append({'id': new_member.id, 'status': 'added'})
        except IntegrityError:
            session.rollback()
            results.append({'id': member_data.get('id'), 'error': 'govid or email already exists'})
        except Exception as e:
            session.rollback()
            results.append({'id': member_data.get('id'), 'error': str(e)})
    try:
        session.commit()
    except Exception as e:
        session.rollback()
        return jsonify({'error': f'Bulk commit failed: {str(e)}', 'results': results}), 500
    finally:
        session.close()
    return jsonify({'results': results}), 200

@app.route('/api/admin/member/<string:member_id>/edit', methods=['POST'])
@admin_auth_required
def edit_member(member_id):
    session = g.session
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        member = session.query(db.Member).filter_by(id=member_id).first()
        if not member:
            return jsonify({"error": f"Member with id {member_id} not found"}), 404

        # Update the member's fields
        for field in [
            "name", "govid", "phone", "birthday", "email", "type"
        ]:
            if field in data:
                setattr(member, field, data[field])

        session.commit()

        return jsonify({"message": f"Member {member_id} updated successfully"}), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

@app.route('/api/admin/member/<string:member_ids>/set-paid', methods=['POST'])
@admin_auth_required
def set_paid_status(member_ids):
    session = g.session
    try:
        data = request.get_json()
        if not data or "paid" not in data:
            return jsonify({"error": "'paid' boolean is required in request body"}), 400

        paid = data["paid"]
        current_year = datetime.today().year

        # Split member_ids by comma and remove whitespace
        member_id_list = [mid.strip() for mid in member_ids.split(',') if mid.strip()]
        if not member_id_list:
            return jsonify({"error": "No valid member_id(s) provided"}), 400

        results = []
        for member_id in member_id_list:
            permit = (
                session.query(db.MemberCardIssuePermit)
                .filter_by(member_id=member_id, year=current_year)
                .first()
            )

            if paid:
                if not permit:
                    # Create a new permit for the year
                    expiry_date = datetime(current_year + 1, 1, 1) - timedelta(days=1)
                    new_permit = db.MemberCardIssuePermit(
                        member_id=member_id,
                        expiry_date=expiry_date.date(),
                        year=current_year
                    )
                    session.add(new_permit)
                    message = "Permit created (paid set)."
                else:
                    message = "Permit already exists (paid already set)."
            else:
                if permit:
                    session.delete(permit)
                    message = "Permit deleted (paid unset)."
                else:
                    message = "No permit to delete (paid already unset)."
            results.append({"member_id": member_id, "message": message})

        session.commit()
        return jsonify({"results": results}), 200

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

@app.route('/api/admin/conferences', methods=['GET'])
@admin_auth_required
def get_conferences():
    session = g.session
    try:
        today_param = request.args.get("today")
        query = session.query(db.Conference)

        if today_param == "1":
            today = datetime.today().date()
            query = query.filter(db.Conference.date == today)

        conferences = query.order_by(db.Conference.date.desc()).all()

        data = [
            {
                "id": conf.id,
                "name": conf.name,
                "date": conf.date.strftime("%Y-%m-%d")
            }
            for conf in conferences
        ]
        return jsonify({"conferences": data}), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

# create a conference
@app.route('/api/admin/conference', methods=['POST'])
@admin_auth_required
def add_conferences():
    session = g.session
    try:
        data = request.get_json()
        name = data.get("name")
        date_str = data.get("date")

        if not name or not date_str:
            return jsonify({"error": "Missing required fields: name and date"}), 400

        # Convert string date to datetime.date
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

        new_conf = db.Conference(name=name, date=date_obj)
        session.add(new_conf)
        session.commit()

        return jsonify({"success": True, "id": new_conf.id}), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

@app.route('/api/admin/conference/<int:conference_id>/check-in-record', methods=['GET'])
@admin_auth_required
def get_checkin_records(conference_id):
    session = g.session
    try:
        # Join CheckInRecord with Member to get member details
        records = (
            session.query(db.CheckInRecord, db.Member)
            .join(db.Member, db.CheckInRecord.member_id == db.Member.id)
            .filter(db.CheckInRecord.conference_id == conference_id)
            .all()
        )
        result = []
        for record, member in records:
            result.append({
                "member_id": record.member_id,
                "time": int(record.time.timestamp()) if record.time else None,
                "name": member.name,
                "email": member.email,
                "phone": member.phone,
            })
        return jsonify(result), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

# write a check in record with qrcode on membercard
@app.route('/api/admin/conference/<conference_id>/check-in', methods=['POST'])
@admin_auth_required
def conference_check_in(conference_id):
    session = g.session
    data = request.get_json()
    qrcode = data["qrcode"]
    print(data)
    try:
        # Retrieve member data based on the QR code
        member_data = session.query(db.Member).filter(db.Member.qrcode==qrcode).first()
        if member_data:
            prev_record = session.query(db.CheckInRecord).filter(and_(db.CheckInRecord.member_id==member_data.id, db.CheckInRecord.conference_id==conference_id)).first()
            if prev_record:
                return jsonify({'name': member_data.name, 'message': 'already created'}), 202
            # Create a new check-in record
            check_in_record = db.CheckInRecord(
                member_id=member_data.id,
                conference_id=conference_id,
                time= datetime.now()
            )
            session.add(check_in_record)
            session.commit()
            return jsonify({'name': member_data.name, 'message': 'Check-in successful'}), 200
        else:
            return jsonify({'message': f'No member found with the provided QR code: {qrcode}'}), 404
    except Exception as e:
        session.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500
    finally:
        session.close()

# login with govid and name
@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    ac = data["account"]
    pw = data["password"]

    if not ac or not pw:
        return jsonify({"error": "account and password are required"}), 400

    session = db.session_local()

    try:
        admin = session.query(db.Admin).filter_by(account=ac).first()
        if not admin or not bcrypt.checkpw(pw.encode('utf-8'), admin.password.encode('utf-8')):
            return jsonify({"error": "no correspond admin data found"}), 404

        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

        # Update user's OTP code in the database
        
        admin.token = token
        admin.token_expiry_time = int(time.time()) + 60 * 60

        session.commit()

        return jsonify({"success": True, "token": token }), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

@app.route('/api/admin/send-invitation-letter', methods=['POST'])
@admin_auth_required
def send_invitation_letter():
    session = g.session
    try:
        data = request.get_json()
        if not data or "member_ids" not in data or not isinstance(data["member_ids"], list):
            return jsonify({"error": "'member_ids' must be a list of strings"}), 400

        member_ids = data["member_ids"]
        current_year = datetime.today().year

        # Fetch all members with permits for the current year
        permits = (
            session.query(db.MemberCardIssuePermit)
            .filter(db.MemberCardIssuePermit.member_id.in_(member_ids))
            .filter(db.MemberCardIssuePermit.year == current_year)
            .all()
        )
        permitted_ids = {p.member_id for p in permits}

        # Fetch member data for those permitted
        permitted_members = (
            session.query(db.Member)
            .filter(db.Member.id.in_(permitted_ids))
            .all()
        )

        # Paths to the email template and attachment
        template_path = os.path.join(os.getcwd(), 'src', 'email_templates', 'invitation.html')

        for member in permitted_members:
            Thread(
                target=util.send_email_with_attachment,
                args=(f"【陽明交大校友總會】歡迎申請 {current_year} 年度會員證", member.email, template_path, None)
            ).start()

        return jsonify({
            "message": f"Invitation letters are being sent to {len(permitted_members)} member(s).",
            "sent_to": [m.email for m in permitted_members]
        }), 200

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

@app.route('/api/admin/update-member-card', methods=['POST'])
@admin_auth_required
def update_member_card_bulk():
    session = g.session
    try:
        data = request.get_json()
        if not data or "member_ids" not in data or not isinstance(data["member_ids"], list):
            return jsonify({"error": "'member_ids' must be a list of strings"}), 400

        member_ids = data["member_ids"]
        current_year = datetime.now().year

        # Load all members
        members = session.query(db.Member).filter(db.Member.id.in_(member_ids)).all()
        members_by_id = {m.id: m for m in members}

        # Check for missing members
        missing_ids = set(member_ids) - set(members_by_id.keys())
        if missing_ids:
            return jsonify({"error": f"Member(s) not found: {', '.join(missing_ids)}"}), 404

        # Load permits
        permits = (
            session.query(db.MemberCardIssuePermit)
            .filter(db.MemberCardIssuePermit.member_id.in_(member_ids))
            .filter(db.MemberCardIssuePermit.year == current_year)
            .all()
        )
        permits_by_member_id = {p.member_id: p for p in permits}

        # Load icons
        icon_dir = os.path.join(os.getcwd(), os.getenv('icons_path'))
        existed_icon = set(os.listdir(icon_dir)) if os.path.exists(icon_dir) else set()

        # Track results
        success_list = []
        error_list = []

        for member_id in member_ids:
            member = members_by_id[member_id]

            # Check permit
            permit = permits_by_member_id.get(member_id)
            if not permit:
                error_list.append({"member": member.name, "error": "No permit"})
                continue

            # Check icon
            if not any(member.govid in fname for fname in existed_icon):
                return jsonify({"error": f"missing icon for {member.name}"}), 400

            # Ensure QR code
            if not member.qrcode:
                member.qrcode = str(uuid.uuid4())
                session.commit()

            # Create pass
            ok, message = pkpass.newpass(member, permit)
            if not ok:
                error_list.append({"member": member.name, "error": message})
                continue

            # Send email
            pkpass_filename = f"{member.qrcode}.pkpass"
            pkpass_path = os.path.join(os.getcwd(), os.getenv('pkfiles_path'), pkpass_filename)
            email_template_path = os.path.join(os.getcwd(), 'src', 'email_templates', 'output.html')

            Thread(
                target=util.send_email_with_attachment,
                args=(f"【陽明交大校友總會】{current_year}年度會員證—寄發信", member.email, email_template_path, pkpass_path)
            ).start()

            success_list.append({"member": member.name, "email": member.email})

        return jsonify({
            "status": "completed",
            "success_count": len(success_list),
            "failed_count": len(error_list),
            "sent": success_list,
            "errors": error_list
        }), 200

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

@app.route('/api/admin/send-member-card', methods=['POST'])
@admin_auth_required
def send_membercards():
    session = g.session
    try:
        data = request.get_json()
        if not data or "member_ids" not in data or not isinstance(data["member_ids"], list):
            return jsonify({"error": "'member_ids' must be a list of strings"}), 400

        member_ids = data["member_ids"]
        current_year = datetime.now().year

        # Load all members
        members = session.query(db.Member).filter(db.Member.id.in_(member_ids)).all()
        members_by_id = {m.id: m for m in members}

        # Check for missing members
        missing_ids = set(member_ids) - set(members_by_id.keys())
        if missing_ids:
            return jsonify({"error": f"Member(s) not found: {', '.join(missing_ids)}"}), 404

        # Load permits
        permits = (
            session.query(db.MemberCardIssuePermit)
            .filter(db.MemberCardIssuePermit.member_id.in_(member_ids))
            .filter(db.MemberCardIssuePermit.year == current_year)
            .all()
        )
        permits_by_member_id = {p.member_id: p for p in permits}

        # Load icons
        icon_dir = os.path.join(os.getcwd(), os.getenv('icons_path'))
        existed_icon = set(os.listdir(icon_dir)) if os.path.exists(icon_dir) else set()

        # Prepare email templates
        invitation_template = os.path.join(os.getcwd(), 'src', 'email_templates', 'invitation.html')
        card_template = os.path.join(os.getcwd(), 'src', 'email_templates', 'output.html')

        successes = []
        skipped = []
        errors = []

        for member_id in member_ids:
            member = members_by_id[member_id]
            permit = permits_by_member_id.get(member_id)
            if not permit:
                skipped.append({"id": member.id, "reason": "No permit"})
                continue

            has_icon = any(member.govid in fname for fname in existed_icon)
            if has_icon:
                # Send member card
                if not member.qrcode:
                    member.qrcode = str(uuid.uuid4())
                    session.commit()
                ok, message = pkpass.newpass(member, permit)
                if not ok:
                    errors.append({"member": member.name, "error": message})
                    continue
                pkpass_filename = f"{member.qrcode}.pkpass"
                pkpass_path = os.path.join(os.getcwd(), os.getenv('pkfiles_path'), pkpass_filename)
                Thread(
                    target=util.send_email_with_attachment,
                    args=(f"【陽明交大校友會】{current_year}年度會員證—寄發信", member.email, card_template, pkpass_path)
                ).start()
                successes.append({"id": member.id, "email": member.email})
            else:
                # Send invitation
                Thread(
                    target=util.send_email_with_attachment,
                    args=(f"【陽明交大校友會】歡迎申請 {current_year} 年度會員證", member.email, invitation_template, None)
                ).start()
                successes.append({"id": member.id, "email": member.email})

        return jsonify({
            "status": "completed",
            "successes": successes,
            "skipped": skipped,
            "errors": errors
        }), 200

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

@app.route('/api/admin/user-info', methods=['GET'])
@admin_auth_required
def get_admin_user_info():
    admin = getattr(g, 'admin', None)
    if not admin:
        return jsonify({'error': 'Admin not found'}), 404
    return jsonify({
        'id': admin.id,
        'account': admin.account,
        'email': admin.email
    }), 200

@app.route('/api/admin/member/<string:member_id>', methods=['DELETE'])
@admin_auth_required
def delete_member(member_id):
    session = g.session
    try:
        member = session.query(db.Member).filter_by(id=member_id).first()
        if not member:
            return jsonify({"error": f"Member with id {member_id} not found"}), 404

        session.delete(member)
        session.commit()
        return jsonify({"message": f"Member {member_id} deleted successfully"}), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()

@app.route('/api/admin/send-member-card/preview', methods=['POST'])
@admin_auth_required
def preview_send_membercards():
    session = g.session
    try:
        data = request.get_json()
        if not data or "member_ids" not in data or not isinstance(data["member_ids"], list):
            return jsonify({"error": "'member_ids' must be a list of strings"}), 400

        member_ids = data["member_ids"]
        current_year = datetime.now().year

        # Load all members
        members = session.query(db.Member).filter(db.Member.id.in_(member_ids)).all()
        members_by_id = {m.id: m for m in members}

        # Load permits
        permits = (
            session.query(db.MemberCardIssuePermit)
            .filter(db.MemberCardIssuePermit.member_id.in_(member_ids))
            .filter(db.MemberCardIssuePermit.year == current_year)
            .all()
        )
        permits_by_member_id = {p.member_id: p for p in permits}

        # Load icons
        icon_dir = os.path.join(os.getcwd(), os.getenv('icons_path'))
        existed_icon = set(os.listdir(icon_dir)) if os.path.exists(icon_dir) else set()

        preview_list = []
        for member_id in member_ids:
            member = members_by_id.get(member_id)
            if not member:
                continue
            permit = permits_by_member_id.get(member_id)
            has_permit = permit is not None
            has_icon = any(member.govid in fname for fname in existed_icon)
            if not has_permit:
                email_type = 'invalid'
            else:
                email_type = 'update_card' if has_icon else 'invitation'
            preview_list.append({
                "id": member.id,
                "name": member.name,
                "permit": has_permit,
                "email_type": email_type
            })

        return jsonify(preview_list), 200

    except Exception as e:
        session.rollback()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500
    finally:
        session.close()