# Sistem Manajemen Inventaris Peralatan Kantor

Aplikasi CLI berbasis Python + MySQL untuk mencatat, melacak, dan mengelola
barang inventaris kantor (komputer, proyektor, meja, dll).

## Peran & Hak Akses

| Peran                  | Hak Akses                                                               |
| ---------------------- | ----------------------------------------------------------------------- |
| **Staf**               | Melihat daftar inventaris, mengajukan permintaan peminjaman             |
| **Petugas Inventaris** | CRUD data barang, menyetujui/menolak peminjaman, memproses pengembalian |
| **Admin**              | Memantau log aktivitas, melihat laporan rekap inventaris & peminjaman   |

## Struktur Project

```
app.py               # business logic (InventorySystem) + CLI
db.py                # Database: wrapper koneksi MySQL (connection pooling)
demo_roles.py         # skrip demo otorisasi peran (Staf/Petugas/Admin)
database/schema.sql  # DDL: users, items, loans, activity_logs
database/seed.sql    # data contoh untuk demo manual
tests/                # unit test (pytest) + FakeDatabase in-memory
```

## Instalasi

```powershell
# 1. Buat virtual environment & install dependency
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. Buat database & tabel
mysql -u root -p < database/schema.sql
mysql -u root -p inventaris_kantor < database/seed.sql   # opsional, data contoh

# 3. Salin file environment lalu sesuaikan kredensial
copy .env.example .env
```

## Menjalankan Aplikasi

```powershell
python app.py
```

Login memakai `user_id` dari tabel `users` (hasil seed: 1=Andi/Staf, 2=Budi/Petugas, 3=Citra/Admin). Menu yang tersedia:

```
1) Lihat daftar barang       2) Rekap inventaris        3) Rekap peminjaman
4) Tambah barang             5) Ajukan pinjam barang    6) Setujui peminjaman
7) Tolak peminjaman          8) Kembalikan barang       9) Log aktivitas (Admin)
0) Keluar
```

Aksi yang tidak sesuai peran akan ditolak dengan pesan `Ditolak: ...`, bukan crash.

Untuk demo cepat otorisasi tiap peran tanpa lewat menu:

```powershell
python demo_roles.py
```

## Menjalankan Test

```powershell
pytest -v
```

Test memakai `FakeDatabase` in-memory (lihat `tests/conftest.py`), jadi tidak butuh koneksi MySQL nyata.
