from db import odbc_conn, mysql_conn

odbc_cursor = odbc_conn.cursor()
mysql_cursor = mysql_conn.cursor()

kode_kabupaten = "040300"

# AMBIL DATA KECAMATAN
def ambil_data_kecamatan():
    odbc_cursor.execute(
        """SELECT DISTINCT kode_kecamatan, kecamatan FROM datamart.sekolah WHERE kode_kabupaten=? ORDER BY kode_kecamatan""",
        kode_kabupaten,
    )

    for index, row in enumerate(odbc_cursor.fetchall()):
        print("{:003d}".format(index + 1), row[1].strip())
        sql = "INSERT INTO kecamatan (id, nama) VALUES (%s, %s) ON DUPLICATE KEY UPDATE nama=%s"
        val = (row[0].strip(), row[1], row[1])
        mysql_cursor.execute(sql, val)
        mysql_conn.commit()


if __name__ == "__main__":
    ambil_data_kecamatan()
