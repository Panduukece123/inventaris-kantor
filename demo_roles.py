"""
Demo otorisasi peran (Staf / Petugas / Admin).
Jalankan: python demo_roles.py

Menunjukkan aksi mana yang BOLEH dan mana yang DITOLAK (PermissionError)
untuk tiap peran, sesuai tabel hak akses di README.
"""
from db import Database
from app import InventorySystem

db = Database()
s = InventorySystem(db)

# user_id hasil seed.sql: 1=Andi(Staf), 2=Budi(Petugas), 3=Citra(Admin)
STAF, PETUGAS, ADMIN = 1, 2, 3


def coba(label, fungsi):
    """Jalankan aksi, cetak hasil ATAU alasan ditolak."""
    try:
        hasil = fungsi()
        print(f"  [BOLEH]  {label} -> {hasil}")
    except PermissionError as e:
        print(f"  [DITOLAK] {label} -> {e}")


print("=== 1. STAF (Andi) ===")
coba("Lihat daftar barang", lambda: s.search_item())
coba("Ajukan pinjam barang id=3", lambda: s.process_loan_request(STAF, 3))
coba("Tambah barang baru", lambda: s.add_item(STAF, "INV-999", "Barang Staf"))
coba("Setujui peminjaman id=1", lambda: s.approve_loan(STAF, 1))
coba("Lihat log aktivitas (khusus Admin)", lambda: s.get_activity_logs(STAF))

print("\n=== 2. PETUGAS (Budi) ===")
coba("Tambah barang baru", lambda: s.add_item(PETUGAS, "INV-998", "Kursi"))
coba("Edit barang id=3", lambda: s.edit_item(PETUGAS, 3, nama_barang="Meja Rapat"))
coba("Setujui peminjaman id=1", lambda: s.approve_loan(PETUGAS, 1))
coba("Lihat log aktivitas (khusus Admin)", lambda: s.get_activity_logs(PETUGAS))

print("\n=== 3. ADMIN (Citra) ===")
coba("Rekap inventaris", lambda: s.get_inventory_recap())
coba("Rekap peminjaman", lambda: s.get_loan_recap())
coba("Lihat log aktivitas", lambda: s.get_activity_logs(ADMIN))
coba("Tambah barang (Admin juga diizinkan)", lambda: s.add_item(ADMIN, "INV-997", "Printer"))
