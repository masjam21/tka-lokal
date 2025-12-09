import uuid
from werkzeug.security import generate_password_hash

from db import odbc_conn, mysql_conn

mysql_cursor = mysql_conn.cursor()

mysql_cursor = mysql_conn.cursor()
mysql_cursor.execute("SELECT id, nama, npsn FROM sekolah ORDER BY nama")

password = generate_password_hash("123456")

for index, row in enumerate(mysql_cursor.fetchall()):
    print("    ", row[1])

    sql = "INSERT INTO user (id, username, nama, role, password, sekolah_id) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE username=%s, nama=%s, password=%s, sekolah_id=%s"
    val = (
        uuid.uuid4(),
        row[2],
        row[1],
        "proktor",
        password,
        row[0],
        row[2],
        row[1],
        password,
        row[0],
    )

    mysql_cursor.execute(sql, val)

mysql_conn.commit()
