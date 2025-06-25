from dotenv import load_dotenv
import os

from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

url = f"mysql+pymysql://{os.getenv('db_user')}:{os.getenv('db_pw')}@{os.getenv('db_host')}/{os.getenv('db_database')}"
engine = create_engine(url, pool_pre_ping=True)
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
    token           = Column(String, nullable=True)
    otpcode         = Column(String, nullable=True)

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
    member_id       = Column(String)
    conference_id   = Column(Integer, nullable=False)
    id              = Column(Integer, primary_key=True)
    time            = Column(DateTime, nullable=False)
