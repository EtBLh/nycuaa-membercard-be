from src import db
from src import util
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

def newpass(member: db.Member):
    name, qrcode, govid, id, type = util.pick(member, 'name','qrcode','govid','id','type')

    current_dir = os.getcwd()
    pass_directory = os.path.join(current_dir, os.getenv('passes_path'), govid)

    file_path = os.path.join(pass_directory, "pass.json")
    with open(file_path, 'r') as file:
        data = json.load(file)
    data['serialNumber'] = govid
    data['webServiceURL'] = "https://nycuaa.org/passes/"
    data['authenticationToken'] = qrcode
    data['barcode']['message'] = qrcode
    data['generic']['primaryFields'][0]['value'] = name
    data['generic']['secondaryFields'][0]['value'] = "2024"

    if type == 'founding':
        data['generic']['auxiliaryFields'][0]['value'] = "普通會員（創始會員）"
    elif type == 'group':
        data['generic']['auxiliaryFields'][0]['value'] = "團體會員"
    else: # type == 'normal'
        data['generic']['auxiliaryFields'][0]['value'] = "普通會員"
    
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
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
    
    return "success"