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

def save_manifest(manifest, output_file):
    with open(output_file, 'w') as f:
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

def newpass(name,qrcode,govid,id):

    current_dir = os.getcwd()
    dir = os.path.join(current_dir, govid)

    file_path = os.path.join(dir, "pass.json")
    with open(file_path, 'r') as file:
        data = json.load(file)
    data['serialNumber'] = govid
    data['webServiceURL'] = "https://nycuaa.org/passes/"
    data['authenticationToken'] = qrcode
    data['barcode']['message'] = qrcode
    data['generic']['primaryFields'][0]['value'] = name
    data['generic']['secondaryFields'][0]['value'] = "2024"
    if (id<2404452):
        data['generic']['auxiliaryFields'][0]['value'] = "普通會員（創始會員）"
    else:
        data['generic']['auxiliaryFields'][0]['value'] = "普通會員"
    # print(data)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
    pass_directory = dir
    wwdr_cert = "/home/ubuntu/membercard/WWDR.pem"
    signer_cert = "/home/ubuntu/membercard/signerCert.pem"
    signer_key = "/home/ubuntu/membercard/signerKey.pem"
    output_file = qrcode

    # Generate the manifest
    manifest = generate_manifest(pass_directory)
    save_manifest(manifest, os.path.join(pass_directory, "manifest.json"))
    print("Manifest generated successfully.")

    # Sign the manifest
    sign_manifest(pass_directory, wwdr_cert, signer_cert, signer_key)
    print("Manifest signed successfully.")

    # Create the .pkpass file
    pkpass.create(pass_directory, output_file)
    print(f"{output_file}.pkpass created successfully.")
    current_dir = os.getcwd()
    src = os.path.join(current_dir, output_file+".pkpass")
    dst = os.path.join("/var/www/pass_files", output_file+".pkpass")
    move_file(src,dst)
    return "success"