from dotenv import load_dotenv
load_dotenv(override=True)

from src import pkpass
from src import db
from src import util
import os

updatemem = [2400121,2400231,2400351,2400391,2400482,2400532,2400842,2401282,2401412,2401592,2401722,2401842,2401872,2401952,2401972,2402262,2402372,2402442,2402532,2402562,2402972,2403032,2403062,2403212,2403252,2403622,2403682,2403872,2403882,2404011,2404021,2404032,2404081,2404132,2404161,2404222,2404462,2504592]

def update_member_card(govid, name):
    try:
        rt = util.fetch_member_by_namegovid("membership.ct4ismqeal59.ap-northeast-1.rds.amazonaws.com","member", "admin", "nycuaa123x", govid, name)
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
    data_ok = True
    session = db.session_local()
    data_ok_members = []
    data_not_ok_members = []
    for idx, memid in enumerate(updatemem):
        memberd = session.member = session.query(db.Member).filter_by(id=memid).first()
        if not memberd:
            print(f'nodbdata: {memid}')
            data_ok = False
            data_not_ok_members.append(memid)
            continue
        passdir = os.path.join(os.getcwd(), os.getenv('passes_path'), memberd.govid)
        if not os.path.exists(passdir):
            print(f'nopassdata: {memid} {memberd.name} {memberd.govid}')
            data_ok = False
            data_not_ok_members.append(memid)
            continue
        data_ok_members.append(memid)
    if not data_ok:
        print('member data are not ok: lack of previous pass or no db row')
    
    print('data ok: ', end='')
    print(data_ok_members)
    print('data not ok: ', end='')
    print(data_not_ok_members)
    


        