#!/usr/bin/env python3
import os
import sys
import traceback
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app import create_app, db
from app.models import User, Sekolah

import requests

# load .env if present
env_path = os.path.join(ROOT, '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k not in os.environ:
                    os.environ[k] = v

# perform simple ${VAR} expansion for SQLALCHEMY_DATABASE_URI if present
if "SQLALCHEMY_DATABASE_URI" in os.environ:
    uri = os.environ["SQLALCHEMY_DATABASE_URI"]
    # replace ${VAR} occurrences
    import re

    def _repl(match):
        name = match.group(1)
        return os.environ.get(name, "")

    uri2 = re.sub(r"\$\{([^}]+)\}", _repl, uri)
    os.environ["SQLALCHEMY_DATABASE_URI"] = uri2


def main():
    app = create_app()
    date_format = "%Y/%m/%d %H:%M"

    with app.app_context():
        try:
            proktor = User.query.filter(User.role == "proktor").first()
            if not proktor:
                print("Tidak ada user dengan role 'proktor' di database lokal.")
                return 1

            sekolah = Sekolah.query.filter(Sekolah.id == proktor.sekolah_id).first()

            peserta = User.query.filter(User.sekolah_id == sekolah.id).all()
            peserta_list = []
            for i in peserta:
                peserta_list.append(
                    {
                        "id": i.id,
                        "username": i.username,
                        "nama": i.nama,
                        "role": i.role,
                        "password": i.password,
                        "sekolah_id": i.sekolah_id,
                        "nis": i.nis,
                        "nik": i.nik,
                        "ibu": i.ibu,
                        "ayah": i.ayah,
                        "alamat": i.alamat,
                        "jenis_kelamin": i.jenis_kelamin,
                        "rombongan_belajar_id": i.rombongan_belajar_id,
                        "tempat_lahir": i.tempat_lahir,
                        "tanggal_lahir": datetime.strftime(i.tanggal_lahir, date_format)
                        if i.tanggal_lahir is not None
                        else None,
                        "created_at": datetime.strftime(i.created_at, date_format)
                        if i.created_at is not None
                        else None,
                        "updated_at": datetime.strftime(i.updated_at, date_format)
                        if i.updated_at is not None
                        else None,
                        "deleted": i.deleted,
                    }
                )

            server_url = os.environ.get("SERVER_CENTRAL_URL")
            api_key = os.environ.get("API_KEY")
            payload = {
                "proktor_id": proktor.id,
                "peserta_didik": peserta_list,
                "latest_update": datetime.strftime(proktor.latest_update, "%Y/%m/%d %H:%M:%S")
                if proktor.latest_update is not None
                else None,
            }

            print(f"Mengirim permintaan ke {server_url}/api/get-data sebagai proktor {proktor.id}...")
            r = requests.post(
                server_url + "/api/get-data",
                json=payload,
                headers={"token": api_key},
                verify=False,
                timeout=30,
            )

            print("Status:", r.status_code)
            try:
                print(r.json())
            except Exception:
                print(r.text)

        except Exception:
            traceback.print_exc()
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
