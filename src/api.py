from flask import Flask,  request, jsonify
import os
from PIL import Image
from io import BytesIO
from src import util
from src import pkpass

# flask app
app = Flask(__name__)

@app.route('/api/check-in/<qrcode>', methods=['POST'])
def qrcode_check_in(qrcode):
    member_data, ok = util.fetch_member_by_qrcode(qrcode)
    if ok:
        if member_data:
            util.checkin_member_by_id(member_data[0])
            return jsonify({'name': member_data[1]}), 200
        else:
            return jsonify({'message': 'no member found'}), 404
    else:
        return jsonify({'message': 'error occured'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    return jsonify({'error': 'not implemented'}), 400 

@app.route('/api/logout', methods=['POST'])
def logout():
    return jsonify({'error': 'not implemented'}), 400

@app.route('/api/user_icon', methods=['GET'])
def get_user_icon():
    return jsonify({'error': 'not implemented'}), 400

@app.route('/api/newpass_by_namegovid', methods=['POST'])
def newpass():
    name = request.args.get('name')
    govid = request.args.get('govid')
    try:
        form_data = request.get_json()
    except Exception as e:
        return jsonify({'error': 'Invalid JSON format'}), 400

    try:
        record = util.fetch_member_by_namegovid(govid, name)
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
    pkpass.newpass(rt[1], rt[7], rt[2], rt[0], rt[6])
    
    dst = os.path.join("/var/www/pass_files", rt[1]+".pkpass")
    send_email_with_attachment("【陽明交大校友總會】2025年度會員證—寄發信", rt[0][5], 'html_template/output.html', dst)
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
        record = util.fetch_member_by_namegovid(govid, name)
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
