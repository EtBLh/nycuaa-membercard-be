from src import db
from src import util
from PIL import Image, ImageFile, ExifTags
import json
import hashlib
import shutil
import subprocess
import os

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

def save_manifest(manifest, output_filename):
    with open(output_filename, 'w') as f:
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

def create(pass_directory, output_file):
    shutil.make_archive(output_file, 'zip', pass_directory)
    os.rename(output_file + '.zip', output_file + '.pkpass')

# make sure member.qrcode is not null or empty string before calling this function
def newpass(member: db.Member, permit: db.MemberCardIssuePermit):
    id, name, email, qrcode, govid, type = util.pick(member, 'id', 'name', 'email', 'qrcode','govid','type')

    # copy pass template to passes/<govid>
    current_dir = os.getcwd()
    source_folder = os.path.join(current_dir, 'src', 'pass_template')
    pass_directory = os.path.join(current_dir, os.getenv('passes_path'), govid)
    if os.path.exists(pass_directory):
        util.delete_folder(pass_directory)
    util.copy_folder(source_folder, pass_directory)

    # copy member's icon to their pass directory
    icon_dir = os.path.join(os.getcwd(), os.getenv('icons_path'))
    icon_name = util.get_icon_name_by_govid(icon_dir, member.govid)
    icon_full_path = os.path.join(icon_dir, icon_name)
    if icon_name:
        image = Image.open(icon_full_path)
        file_path = os.path.join(icon_dir, icon_name)
        #convert image to PNG
        image.save(icon_full_path, 'PNG')

        #save thumbnail
        file_path = os.path.join(pass_directory, "thumbnail@2x.png")
        image.thumbnail((640,640))
        image.save(file_path, 'PNG')

        #save thumbnail
        file_path = os.path.join(pass_directory, "thumbnail.png")
        image.thumbnail((320,320))
        image.save(file_path, 'PNG')
    else:
        delete_folder(pass_directory)
        return False, 'icon_missing'

    # open the member's pass.json 
    pass_json = os.path.join(pass_directory, "pass.json")
    with open(pass_json, 'r') as pass_json_file:
        data = json.load(pass_json_file)

    # editing the pass.json 
    data['serialNumber'] = govid
    data['authenticationToken'] = qrcode
    data['barcode']['message'] = qrcode
    data['barcode']['altText'] = str(id)

    data['generic']['primaryFields'][0]['value'] = name
    data['generic']['secondaryFields'][0]['value'] = "20" + str(id)[:2]
    data['generic']['auxiliaryFields'][0]['value'] = permit.expiry_date.strftime("%Y/%m/%d")
    
    # back field
    data['generic']['backFields'][0]['value'] = str(id) # member id
    data['generic']['backFields'][1]['value'] = email

    if type == 'founding':
        data['generic']['auxiliaryFields'][0]['value'] = "普通會員（創始會員）"
    elif type == 'group':
        data['generic']['auxiliaryFields'][0]['value'] = "團體會員"
    else: # type == 'normal'
        data['generic']['auxiliaryFields'][0]['value'] = "普通會員"
    
    # save the member's pass.json 
    with open(pass_json, 'w') as pass_json_file:
        json.dump(data, pass_json_file, indent=4)
    
    wwdr_cert = os.getenv('wwdr_cert_path')
    signer_cert = os.getenv('signer_cert_path')
    signer_key = os.getenv('signer_key_path')
    output_filename = qrcode

    # Generate the manifest
    manifest = generate_manifest(pass_directory)
    save_manifest(manifest, os.path.join(pass_directory, "manifest.json"))
    print("Manifest generated successfully.")

    # Sign the manifest
    sign_manifest(pass_directory, wwdr_cert, signer_cert, signer_key)
    print("Manifest signed successfully.")

    # Create the .pkpass file
    create(pass_directory, os.path.join(os.getcwd(), os.getenv('pkfiles_path'), output_filename))
    print(f"{output_filename}.pkpass created successfully.")
    
    return True, "success"