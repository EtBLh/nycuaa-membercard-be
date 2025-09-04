from dotenv import load_dotenv
import os
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Boolean, Enum
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

url = f"mysql+pymysql://{os.getenv('db_user')}:{os.getenv('db_pw')}@{os.getenv('db_host')}/{os.getenv('db_database')}"
engine = create_engine(url, pool_pre_ping=True)
session_local = sessionmaker(bind=engine)
print('[+] db connected')
Base = declarative_base()

class Member(Base):
    __tablename__   = 'member_id'
    id              = Column(Integer, primary_key=True)
    name            = Column(String, nullable=True)
    govid           = Column(String, unique=True, nullable=False)
    phone           = Column(String, nullable=True)
    birthday        = Column(String, nullable=True)
    email           = Column(String, unique=True, nullable=False)
    type            = Column(String, nullable=True)
    qrcode          = Column(String, nullable=True)
    token           = Column(String, nullable=True)
    otpcode         = Column(String, nullable=True)

class MemberCardIssuePermit(Base):
    __tablename__   = "card_issue_permit"
    id              = Column(Integer, primary_key=True)
    member_id       = Column(Integer)
    expiry_date     = Column(Date)
    year            = Column(Integer)

class Admin(Base):
    __tablename__       = "admin"
    id                  = Column(Integer, primary_key=True)
    account             = Column(String)
    email               = Column(String)
    password            = Column(String)
    token               = Column(String, nullable=True)
    token_expiry_time   = Column(Integer, nullable=True)

class Conference(Base):
    __tablename__       = "conference"
    id                  = Column(Integer, primary_key=True)
    name                = Column(String)
    date                = Column(Date)

class CheckInRecord(Base):
    __tablename__   = "checkin_record"
    member_id       = Column(Integer)
    conference_id   = Column(Integer, nullable=False)
    id              = Column(Integer, primary_key=True)
    time            = Column(DateTime, nullable=False)

class Log(Base):
    __tablename__   = "log"
    id              = Column(Integer, primary_key=True, autoincrement=True)
    initiator_type  = Column(Enum('admin', 'member', name='initiator_type_enum'), nullable=False)
    initiator       = Column(Integer, nullable=False)
    is_success      = Column(Boolean, nullable=False)
    message         = Column(String(100), nullable=False)
    event_type      = Column(Enum('create_admin', 'delete_admin', 'modify_admin', 'add_member', 'modify_member', 'delete_member', 'issue_membercard', 'send_invitation_email', 'member_login_request', 'member_login_success', 'member_upload_icon', 'admin_login', 'admin_set_paid_status', 'admin_create_conference', 'admin_send_member_card', 'admin_update_member_card', name='event_type_enum'), nullable=False)
    timestamp       = Column(DateTime, nullable=False, default=datetime.now)