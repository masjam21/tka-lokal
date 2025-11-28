from os import environ
import MySQLdb
import pyodbc
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv(".env")

odbc_conn = pyodbc.connect(
    "DRIVER={};SERVER={};DATABASE={};UID={};PWD={};TrustServerCertificate=Yes".format(
        "{ODBC Driver 18 for SQL Server}",
        environ.get("DATAMART_HOST"),
        environ.get("DATAMART_NAME"),
        environ.get("DATAMART_USER"),
        environ.get("DATAMART_PASS"),
    )
)

mysql_conn = MySQLdb.connect(
    host=environ.get("DB_HOST"),
    user=environ.get("DB_USER"),
    passwd=environ.get("DB_PASS"),
    db=environ.get("DB_NAME"),
)
