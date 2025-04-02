from mysql.connector import pooling
from dotenv import load_dotenv
import os

# mysql connection pool
pool = pooling.MySQLConnectionPool(
    pool_name="membercard_db_pool",
    pool_size=5,
    host=os.getenv('db_host'),
    user=os.getenv('db_user'),
    password=os.getenv('db_pw'),
    database=os.getenv('db_database')
)
