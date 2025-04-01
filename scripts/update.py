#! ./bin/python3.12
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
from test import send_email_with_attachment
from server import *
from test import *
import math

pass2beupdateid = [
    "N126264604",
    "F130563570",
    "A127551338",
    "F229462368",
    "E125341212",
    "O200553931",
    "A229658118",
    "A130793439",
    "T124397936",
    "R224402852",
    "D121545624",
    "F800017452",
    "N124521375",
    "D120652291",
    "P122457186",
    "F124158787",
    "E124048187",
    "R120608356",
    "Q123841138",
    "A125221275",
    "R124116920",
    "A127388200",
    "F127331019",
    "N120396349",
    "T223450196",
    "L123988089",
    "A125956782",
    "A126898976",
    "G121926122",
    "E222509045",
    "F126490242",
    "L222966036",
    "A127057933",
    "U121819007",
    "A225914731",
    "T120356939",
    "T120233191",
    "A126010187",
    "S123088142",
    "Q121616968",
    "S124046979",
    "U120300465",
    "N125198030",
    "H123913384",
    "C120747169",
    "S123417545",
    "A122116544",
    "A222417155",
    "A128941890",
    "U121051327",
    "D123048360",
    "A226202472",
    "B120843790",
    "N224423483",
    "Q220593548",
    "B121424459",
    "P220365212",
    "M220779287",
    "E125698645",
    "Y120262588",
    "J222613762",
    "C120429568",
    "H221111982",
    "Q121787828",
    "S123587702",
    "E124440501",
    "K222440920",
    "W100357649",
    "P122138622",
    "S120859532",
    "R123578060",
    "A129895502",
    "A222435957",
    "D123002248",
    "F229445401",
    "F229609530",
    "E121115396",
    "I100091040",
    "S222511564",
    "A210454111",
    "R121564102",
    "K120213094",
    "N124085570",
    "A124115527",
    "T123812149",
    "H124542067",
]

pass2beupdatename = [
    "王成銘",
    "朱軒立",
    "何家慈",
    "李昕穎",
    "林威丞",
    "翁逸芯",
    "梁家語",
    "陳品銓",
    "程柏嘉",
    "顏郁珊",
    "王勝永",
    "史昆靈",
    "江孟庭",
    "佘永吉",
    "吳智斌",
    "李佳哲",
    "沈煒庭",
    "林宜賢",
    "林鴻宇",
    "柯俊先",
    "翁瑋駿",
    "區壬豪",
    "張秉浩",
    "莊人祥",
    "莊惠雯",
    "郭子豪",
    "郭書廷",
    "陳宥霖",
    "陳昱帆",
    "陳珏曇",
    "陳震寰",
    "游舒婷",
    "馮天麒",
    "黃一城",
    "黃莉婷",
    "楊南屏",
    "葉瑞安",
    "劉志東",
    "劉威志",
    "蔡宏明",
    "蔡孟錡",
    "鄭子豪",
    "蕭皓軒",
    "賴建宇",
    "鮑俊傑",
    "薛敦品",
    "聶忠良",
    "藍雅玲",
    "羅士傑",
    "蘇文杰",
    "陳德範",
    "朱儀珊",
    "姜長安",
    "王妙鷹",
    "吳淑芳",
    "林忠誠",
    "陳怡如",
    "陳莉姍",
    "楊鈞任",
    "劉文章",
    "劉思瑜",
    "劉遠祺",
    "簡紫育",
    "羅清池",
    "吳昱錚",
    "李睿仁",
    "張庭棻",
    "符立典",
    "陳益智",
    "蔡益堅",
    "賴柏翰",
    "顏家珩",
    "譚麗玲",
    "王吉磊",
    "李昀真",
    "林佑倫",
    "林奇宏",
    "李育賢",
    "侯旻伶",
    "翁芬華",
    "梁祐維",
    "郭加泳",
    "陳冠誠",
    "詹大千",
    "謝侑霖",
    "劉騏",
]

def newpass(name,qrcode,dir,govid,id):
    file_path = os.path.join(dir, "pass.json")
    with open(file_path, 'r') as file:
        data = json.load(file)
    data['serialNumber'] = govid
    data['webServiceURL'] = "https://nycuaa.org/passes/"
    data['authenticationToken'] = qrcode
    data['barcode']['message'] = qrcode
    data['generic']['primaryFields'][0]['value'] = name
    data['generic']['secondaryFields'][0]['value'] = str(2000+math.floor(id / 100000))
    data['generic']['auxiliaryFields'][1]['value'] = "2025/12/31"
    data['generic']['backFields'] = []
    if (id<2404452):
        data['generic']['auxiliaryFields'][0]['value'] = "普通會員（創始會員）"
    else:
        data['generic']['auxiliaryFields'][0]['value'] = "普通會員"

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

def update_member_card(govid, name):
    try:
        rt = util.fetch_user_by_nameid("membership.ct4ismqeal59.ap-northeast-1.rds.amazonaws.com","member", "admin", "nycuaa123x", govid, name)
    except Exception as e:
        return jsonify({'error': 'No user found'}), 400
    if (len(rt)==0 ):
        return jsonify({'error': 'No user found'}), 400
    current_dir = os.getcwd()
    source_folder = os.path.join(current_dir, 'passes/'+govid)
    destination_folder = os.path.join(os.path.join(current_dir, 'newpasses'),govid)
    copy_folder(source_folder, destination_folder)
    newpass(rt[0][1],rt[1],destination_folder,rt[0][2],rt[0][0])
    dst = os.path.join("/var/www/pass_files", rt[1]+".pkpass")
    send_email_with_attachment(rt[0][5],dst)

if __name__ == '__main__':
    for idx, name in enumerate(pass2beupdatename):
        id = pass2beupdateid[idx]
        update_member_card(id, name)

        