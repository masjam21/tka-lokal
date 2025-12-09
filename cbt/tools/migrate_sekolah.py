from db import odbc_conn, mysql_conn

odbc_cursor = odbc_conn.cursor()
mysql_cursor = mysql_conn.cursor()

kode_kabupaten = "040300"

# AMBIL SEKOLAH 5=SD 9=MI
def ambil_data_sekolah():
    odbc_cursor.execute(
        "SELECT * FROM datamart.sekolah WHERE kode_kabupaten=? AND bentuk_pendidikan_id in (5,9) AND soft_delete_sekolah=0 ORDER BY nama",
        kode_kabupaten,
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
    query = """
        SELECT ptk_id, ptk.sekolah_id, ptk.nama, nip, jenis_ptk_id, no_hp, soft_delete_ptk, s.nama as nama_sekolah
        FROM Datamart.datamart.ptk ptk
        JOIN Datamart.datamart.sekolah s
        ON ptk.sekolah_id = s.sekolah_id
        WHERE s.kode_kabupaten=? AND s.bentuk_pendidikan_id in (5,9) AND ptk.soft_delete_ptk=0 AND ptk.jenis_ptk_id='20' AND s.soft_delete_sekolah=0
        ORDER BY s.nama;
    """
    odbc_cursor.execute(query, kode_kabupaten)
    for index, row in enumerate(odbc_cursor.fetchall()):
        print("{:003d}".format(index + 1), row.nama_sekolah, row.nama)
        sql = "UPDATE sekolah SET kepala_sekolah=%s, no_hp_kepala_sekolah=%s, nip_kepala_sekolah=%s WHERE id=%s"
        val = (row.nama, row.no_hp, row.nip, row.sekolah_id)
        mysql_cursor.execute(sql, val)
        mysql_conn.commit()


# AMBIL ROMBEL
def ambil_data_rombongan_belajar():
    query = """
        SELECT rb.rombongan_belajar_id, rb.tingkat_pendidikan_id, rb.nama, rb.sekolah_id, s.nama as nama_sekolah
        FROM Datamart.datamart.rombongan_belajar rb 
        JOIN Datamart.datamart.sekolah s
        ON rb.sekolah_id = s.sekolah_id
        WHERE s.kode_kabupaten = ? AND s.soft_delete_sekolah = 0 
        AND s.bentuk_pendidikan_id in (5,9) AND rb.soft_delete = 0 
        AND rb.tingkat_pendidikan_id in (6)
        ORDER BY s.nama;
    """

    odbc_cursor.execute(query, kode_kabupaten)

    for index, row in enumerate(odbc_cursor.fetchall()):
        print("{:003d}".format(index + 1), row.nama_sekolah, row.nama)
        sql = "INSERT INTO rombongan_belajar (id, sekolah_id, tingkat_pendidikan, nama) VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE sekolah_id=%s, tingkat_pendidikan=%s, nama=%s"
        val = (
            row.rombongan_belajar_id,
            row.sekolah_id,
            row.tingkat_pendidikan_id,
            row.nama,
            row.sekolah_id,
            row.tingkat_pendidikan_id,
            row.nama,
        )
        mysql_cursor.execute(sql, val)
        mysql_conn.commit()


if __name__ == "__main__":
    print("---AMBIL DATA SEKOLAH---")
    ambil_data_sekolah()
    print("---AMBIL DATA KEPALA SEKOLAH---")
    ambil_data_kepala_sekolah()
    print("---AMBIL DATA ROMBEL---")
    ambil_data_rombongan_belajar()
