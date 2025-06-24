import argparse
import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from src import db


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def add_admin(account: str, password: str):
    session = db.session_local()
    hashed_pw = hash_password(password)

    new_admin = db.Admin(
        account=account,
        password=hashed_pw,
    )

    session.add(new_admin)
    session.commit()
    print(f"Admin user '{account}' added.")

def main():
    parser = argparse.ArgumentParser(description="Add a new admin user.")
    parser.add_argument("account", type=str, help="Admin account name")
    parser.add_argument("password", type=str, help="Admin password")

    args = parser.parse_args()
    add_admin(args.account, args.password)

if __name__ == "__main__":
    main()
