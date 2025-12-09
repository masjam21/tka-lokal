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


# AMBIL SEKOLAH 5=SD 9=MI
def ambil_data_sekolah(kode_sekolah=5):
    odbc_cursor.execute(
        "SELECT * FROM datamart.sekolah WHERE kode_kabupaten=? AND bentuk_pendidikan_id=? AND soft_delete_sekolah=0 ORDER BY nama",
        kode_kabupaten,
        kode_sekolah,
    )

    for index, row in enumerate(odbc_cursor.fetchall()):
        print("{:003d}".format(index + 1), row.nama)

        sql = "INSERT INTO sekolah (id, nama, npsn, kecamatan_id, alamat, email) VALUES (%s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE nama=%s, npsn=%s, kecamatan_id=%s, alamat=%s, email=%s"

        val = (
            row.sekolah_id,
            row.nama,
            row.npsn,
            row.kode_kecamatan.strip(),
            row.alamat_jalan,
            row.email,
            row.nama,
            row.npsn,
            row.kode_kecamatan.strip(),
            row.alamat_jalan,
            row.email,
        )
        mysql_cursor.execute(sql, val)
        mysql_conn.commit()


# AMBIL KEPALA SEKOALAH & TAMBAH PROCTOR
def ambil_data_kepala_sekolah():
    mysql_cursor.execute("SELECT id, nama FROM sekolah ORDER BY nama")

    for index, row in enumerate(mysql_cursor.fetchall()):

        query = "SELECT * FROM datamart.ptk WHERE sekolah_id=? AND jenis_ptk_id=? AND soft_delete_ptk=0"
        odbc_cursor.execute(query, row[0], 20)
        result = odbc_cursor.fetchone()
        if result is not None:
            print("{:003d}".format(index + 1), row[1], result.nama)
            sql = "UPDATE sekolah SET kepala_sekolah=%s, no_hp_kepala_sekolah=%s, nip_kepala_sekolah=%s WHERE id=%s"
            val = (result.nama, result.no_hp, result.nip, row[0])
            mysql_cursor.execute(sql, val)
            mysql_conn.commit()
        else:
            print("{:003d}".format(index + 1), row[1], "-")


# AMBIL ROMBEL
def ambil_data_rombongan_belajar():
    mysql_cursor.execute("SELECT id, nama FROM sekolah ORDER BY nama")

    for index, row in enumerate(mysql_cursor.fetchall()):
        query = "SELECT * FROM datamart.rombongan_belajar WHERE sekolah_id=? AND soft_delete=0"
        odbc_cursor.execute(query, row[0])
        rows = odbc_cursor.fetchall()
        print("{:003d}".format(index + 1), row[1])
        for result in rows:
            print("    ", result.nama)
            sql = "INSERT INTO rombongan_belajar (id, sekolah_id, tingkat_pendidikan, nama) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE sekolah_id=%s, tingkat_pendidikan=%s, nama=%s"
            val = (
                result.rombongan_belajar_id,
                result.sekolah_id,
                result.tingkat_pendidikan_id,
                result.nama,
                result.sekolah_id,
                result.tingkat_pendidikan_id,
                result.nama,
            )
            mysql_cursor.execute(sql, val)
            mysql_conn.commit()


# AMBIL SISWA
def ambil_data_peserta_didik():

    mysql_cursor.execute("SELECT id, nama FROM sekolah ORDER BY nama")
    list_sekolah = mysql_cursor.fetchall()

    for index, row in enumerate(list_sekolah):
        print("{:003d}".format(index + 1), row[1])

        query = "SELECT * FROM datamart.peserta_didik WHERE sekolah_id=? AND soft_delete_peserta_didik=0"

        odbc_cursor.execute(query, row[0])

        for peserta in odbc_cursor.fetchall():
            print("    ", peserta.nama)

            password = (
                generate_password_hash(peserta.nisn) if peserta.nisn is not None else ""
            )

            sql = "INSERT INTO user (id, username, nama, role, password, sekolah_id, nik, ibu, ayah, alamat, jenis_kelamin, rombongan_belajar_id, tempat_lahir, tanggal_lahir) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE username=%s, nama=%s, password=%s, sekolah_id=%s, nik=%s, ibu=%s, ayah=%s, alamat=%s, jenis_kelamin=%s, rombongan_belajar_id=%s, tempat_lahir=%s, tanggal_lahir=%s"
            val = (
                peserta.peserta_didik_id,
                peserta.nisn,
                peserta.nama,
                "peserta_didik",
                password,
                peserta.sekolah_id,
                peserta.nik,
                peserta.nama_ibu_kandung,
                peserta.nama_ayah,
                peserta.alamat_jalan,
                peserta.jenis_kelamin,
                peserta.rombongan_belajar_id,
                peserta.tempat_lahir,
                peserta.tanggal_lahir,
                peserta.nisn,
                peserta.nama,
                password,
                peserta.sekolah_id,
                peserta.nik,
                peserta.nama_ibu_kandung,
                peserta.nama_ayah,
                peserta.alamat_jalan,
                peserta.jenis_kelamin,
                peserta.rombongan_belajar_id,
                peserta.tempat_lahir,
                peserta.tanggal_lahir,
            )

            mysql_cursor.execute(sql, val)

        mysql_conn.commit()


print("---AMBIL DATA KECAMATAN---")
ambil_data_kecamatan()
print("---AMBIL DATA SD---")
ambil_data_sekolah(5)
print("---AMBIL DATA MI---")
ambil_data_sekolah(9)
print("---AMBIL DATA KEPALA SEKOLAH---")
ambil_data_kepala_sekolah()
print("---AMBIL DATA ROMBEL---")
ambil_data_rombongan_belajar()
print("---AMBIL DATA PESERTA---")
ambil_data_peserta_didik()
