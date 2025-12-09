from db import odbc_conn, mysql_conn
from werkzeug.security import generate_password_hash

odbc_cursor = odbc_conn.cursor()
mysql_cursor = mysql_conn.cursor()

kode_kabupaten = "040300"

# AMBIL SISWA
def ambil_data_peserta_didik():
    query = """
        SELECT pd.peserta_didik_id, pd.nama, pd.sekolah_id, pd.nisn, pd.nik, pd.nama_ibu_kandung, 
        pd.nama_ayah, pd.alamat_jalan, pd.jenis_kelamin, pd.rombongan_belajar_id, 
        pd.tempat_lahir, pd.tanggal_lahir, s.nama as nama_sekolah
        FROM Datamart.datamart.peserta_didik pd  
        JOIN Datamart.datamart.sekolah s
        ON pd.sekolah_id = s.sekolah_id
        JOIN Datamart.datamart.rombongan_belajar rb
        ON pd.rombongan_belajar_id = rb.rombongan_belajar_id
        WHERE s.kode_kabupaten = ? AND s.bentuk_pendidikan_id in (5,9) AND s.soft_delete_sekolah = 0 
        AND pd.soft_delete_peserta_didik = 0 AND rb.tingkat_pendidikan_id in (6);
    """
    odbc_cursor.execute(query, kode_kabupaten)

    password = generate_password_hash("password")

    for index, row in enumerate(odbc_cursor.fetchall()):
        print("{:003d}".format(index + 1), row.nama_sekolah, row.nama)

        sql = "INSERT INTO user (id, username, nama, role, password, sekolah_id, nik, ibu, ayah, alamat, jenis_kelamin, rombongan_belajar_id, tempat_lahir, tanggal_lahir) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE username=%s, nama=%s, password=%s, sekolah_id=%s, nik=%s, ibu=%s, ayah=%s, alamat=%s, jenis_kelamin=%s, rombongan_belajar_id=%s, tempat_lahir=%s, tanggal_lahir=%s"
        val = (
            row.peserta_didik_id,
            row.nisn,
            row.nama,
            "peserta_didik",
            password,
            row.sekolah_id,
            row.nik,
            row.nama_ibu_kandung,
            row.nama_ayah,
            row.alamat_jalan,
            row.jenis_kelamin,
            row.rombongan_belajar_id,
            row.tempat_lahir,
            row.tanggal_lahir,
            row.nisn,
            row.nama,
            password,
            row.sekolah_id,
            row.nik,
            row.nama_ibu_kandung,
            row.nama_ayah,
            row.alamat_jalan,
            row.jenis_kelamin,
            row.rombongan_belajar_id,
            row.tempat_lahir,
            row.tanggal_lahir,
        )

        mysql_cursor.execute(sql, val)

    mysql_conn.commit()


if __name__ == "__main__":
    print("---AMBIL DATA PESERTA DIDIK---")
    ambil_data_peserta_didik()
