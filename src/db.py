from dotenv import load_dotenv
import os

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Date
from sqlalchemy.orm import sessionmaker, declarative_base

url = f"mysql+pymysql://{os.getenv('db_user')}:{os.getenv('db_pw')}@{os.getenv('db_host')}/{os.getenv('db_database')}"
engine = create_engine(url)
session_local = sessionmaker(bind=engine)
Base = declarative_base()

class Member(Base):
    __tablename__   = 'member_id'
    id              = Column(String, primary_key=True)
    name            = Column(String, nullable=True)
    govid           = Column(String, unique=True, nullable=False)
    phone           = Column(String, nullable=True)
    birthday        = Column(String, nullable=True)
    email           = Column(String, unique=True, nullable=False)
    type            = Column(String, nullable=True)
    qrcode          = Column(String, nullable=True)
    token           = Column(String, unique=True)
    otpcode         = Column(String, unique=True)

class CheckInRecord(Base):
    __tablename__   = "checkin_record"
    id              = Column(Integer, primary_key=True)
    member_id       = Column(String)
    datetime        = Column(DateTime, nullable=True)

class MemberCardIssuePermit(Base):
    __tablename__   = "card_issue_permit"
    id              = Column(Integer, primary_key=True)
    member_id       = Column(String)
    expiry_date     = Column(Date)
    year            = Column(Integer)

class Admin(Base):
    __tablename__       = "admin"
    id                  = Column(Integer, primary_key=True)
    account             = Column(String)
    password            = Column(Date)
    token               = Column(String)
    token_expiry_time   = Column(Integer)