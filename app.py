"""
Berisi business logic akses basis data untuk 3 peran pengguna:
- Staf     : melihat inventaris & mengajukan peminjaman
- Petugas  : CRUD barang, menyetujui/menolak/memproses pengembalian
- Admin    : melihat log aktivitas & laporan rekap

"""

ROLE_STAF = "Staf"
ROLE_PETUGAS = "Petugas"
ROLE_ADMIN = "Admin"

ITEM_STATUSES = {"Tersedia", "Dipinjam", "Rusak"}


class InventorySystem:
    def __init__(self, db_connection):
        self.db = db_connection

   
    # Helper internal: pengguna & otorisasi
   
    def _get_user(self, user_id: int):
        return self.db.query(
            "SELECT id, nama, role FROM users WHERE id = %s", (user_id,)
        )

    def _require_role(self, user_id: int, allowed_roles: set):
        user = self._get_user(user_id)
        if not user:
            raise ValueError(f"Pengguna id={user_id} tidak ditemukan")
        if user["role"] not in allowed_roles:
            raise PermissionError(
                f"Peran '{user['role']}' tidak diizinkan melakukan aksi ini"
            )
        return user

    def _log_activity(self, user_id: int, aksi: str, keterangan: str = ""):
        self.db.execute(
            "INSERT INTO activity_logs (user_id, aksi, keterangan) VALUES (%s, %s, %s)",
            (user_id, aksi, keterangan),
        )

   
    # Manajemen Barang (Petugas & Admin)
   
    def add_item(self, user_id: int, kode_barang: str, nama_barang: str) -> int:
        self._require_role(user_id, {ROLE_PETUGAS, ROLE_ADMIN})
        if self.db.query("SELECT id FROM items WHERE kode_barang = %s", (kode_barang,)):
            raise ValueError(f"Kode barang '{kode_barang}' sudah digunakan")

        new_id = self.db.execute(
            "INSERT INTO items (kode_barang, nama_barang) VALUES (%s, %s)",
            (kode_barang, nama_barang),
        )
        self._log_activity(user_id, "TAMBAH_BARANG", f"Menambahkan barang {kode_barang}")
        return new_id

    def edit_item(self, user_id: int, item_id: int, nama_barang: str = None,
                  status: str = None) -> bool:
        self._require_role(user_id, {ROLE_PETUGAS, ROLE_ADMIN})
        if not self.db.query("SELECT id FROM items WHERE id = %s", (item_id,)):
            return False

        fields = {}
        if nama_barang is not None:
            fields["nama_barang"] = nama_barang
        if status is not None:
            if status not in ITEM_STATUSES:
                raise ValueError(f"Status '{status}' tidak valid")
            fields["status"] = status
        if not fields:
            return False

        set_clause = ", ".join(f"{column} = %s" for column in fields)
        params = tuple(fields.values()) + (item_id,)
        self.db.execute(f"UPDATE items SET {set_clause} WHERE id = %s", params)
        self._log_activity(user_id, "EDIT_BARANG", f"Mengubah barang id={item_id}")
        return True

    def delete_item(self, user_id: int, item_id: int) -> bool:
        self._require_role(user_id, {ROLE_PETUGAS, ROLE_ADMIN})
        item = self.db.query("SELECT status FROM items WHERE id = %s", (item_id,))
        if not item:
            return False
        if item["status"] == "Dipinjam":
            raise ValueError("Barang sedang dipinjam, tidak bisa dihapus")

        self.db.execute("DELETE FROM items WHERE id = %s", (item_id,))
        self._log_activity(user_id, "HAPUS_BARANG", f"Menghapus barang id={item_id}")
        return True

    def search_item(self, keyword: str = None, status: str = None):
        """Semua peran boleh melihat/mencari daftar inventaris."""
        sql = "SELECT id, kode_barang, nama_barang, status FROM items WHERE 1=1"
        params = []
        if keyword:
            sql += " AND (nama_barang LIKE %s OR kode_barang LIKE %s)"
            like = f"%{keyword}%"
            params += [like, like]
        if status:
            if status not in ITEM_STATUSES:
                raise ValueError(f"Status '{status}' tidak valid")
            sql += " AND status = %s"
            params.append(status)
        return self.db.query_all(sql, tuple(params))

   
    # Peminjaman Barang
   
    def process_loan_request(self, user_id: int, item_id: int) -> bool:
        """
        Memproses pengajuan peminjaman barang oleh Staf.
        Membuat baris `loans` berstatus 'Pending', menunggu persetujuan Petugas.

        :param user_id: ID pengguna yang mengajukan
        :param item_id: ID barang yang ingin dipinjam
        :return: True jika pengajuan berhasil dibuat, False jika barang tidak tersedia
        """
        self._require_role(user_id, {ROLE_STAF, ROLE_PETUGAS, ROLE_ADMIN})

        item = self.db.query("SELECT status FROM items WHERE id = %s", (item_id,))
        if not item or item["status"] != "Tersedia":
            return False

        ongoing = self.db.query(
            "SELECT id FROM loans WHERE item_id = %s AND status_pinjam IN ('Pending', 'Disetujui')",
            (item_id,),
        )
        if ongoing:
            return False

        self.db.execute(
            "INSERT INTO loans (user_id, item_id, tanggal_pinjam, status_pinjam) "
            "VALUES (%s, %s, CURDATE(), 'Pending')",
            (user_id, item_id),
        )
        self._log_activity(user_id, "AJUKAN_PINJAM", f"Mengajukan pinjam barang id={item_id}")
        return True

    def approve_loan(self, user_id: int, loan_id: int) -> bool:
        """Petugas menyetujui pengajuan peminjaman yang berstatus Pending."""
        self._require_role(user_id, {ROLE_PETUGAS, ROLE_ADMIN})

        loan = self.db.query(
            "SELECT item_id, status_pinjam FROM loans WHERE id = %s", (loan_id,)
        )
        if not loan or loan["status_pinjam"] != "Pending":
            return False

        self.db.execute(
            "UPDATE loans SET status_pinjam = 'Disetujui', tanggal_pinjam = CURDATE() "
            "WHERE id = %s",
            (loan_id,),
        )
        self.db.execute(
            "UPDATE items SET status = 'Dipinjam' WHERE id = %s", (loan["item_id"],)
        )
        self._log_activity(user_id, "SETUJUI_PINJAM", f"Menyetujui peminjaman id={loan_id}")
        return True

    def reject_loan(self, user_id: int, loan_id: int) -> bool:
        """Petugas menolak pengajuan peminjaman yang berstatus Pending."""
        self._require_role(user_id, {ROLE_PETUGAS, ROLE_ADMIN})

        loan = self.db.query("SELECT status_pinjam FROM loans WHERE id = %s", (loan_id,))
        if not loan or loan["status_pinjam"] != "Pending":
            return False

        self.db.execute(
            "UPDATE loans SET status_pinjam = 'Ditolak' WHERE id = %s", (loan_id,)
        )
        self._log_activity(user_id, "TOLAK_PINJAM", f"Menolak peminjaman id={loan_id}")
        return True

    def return_loan(self, user_id: int, loan_id: int, kondisi: str = "Tersedia") -> bool:
        """Petugas memproses pengembalian barang. `kondisi` menentukan status akhir barang."""
        self._require_role(user_id, {ROLE_PETUGAS, ROLE_ADMIN})
        if kondisi not in {"Tersedia", "Rusak"}:
            raise ValueError("Kondisi pengembalian harus 'Tersedia' atau 'Rusak'")

        loan = self.db.query(
            "SELECT item_id, status_pinjam FROM loans WHERE id = %s", (loan_id,)
        )
        if not loan or loan["status_pinjam"] != "Disetujui":
            return False

        self.db.execute(
            "UPDATE loans SET status_pinjam = 'Dikembalikan', tanggal_kembali = CURDATE() "
            "WHERE id = %s",
            (loan_id,),
        )
        self.db.execute(
            "UPDATE items SET status = %s WHERE id = %s", (kondisi, loan["item_id"])
        )
        self._log_activity(
            user_id, "KEMBALIKAN_BARANG",
            f"Mengembalikan barang untuk peminjaman id={loan_id} kondisi={kondisi}",
        )
        return True

   
    # Status Barang
   
    def get_item_status(self, item_id: int):
        return self.db.query("SELECT status FROM items WHERE id = %s", (item_id,))

    def list_items_by_status(self, status: str):
        if status not in ITEM_STATUSES:
            raise ValueError(f"Status '{status}' tidak valid")
        return self.db.query_all(
            "SELECT id, kode_barang, nama_barang, status FROM items WHERE status = %s",
            (status,),
        )

   
    # Laporan (Admin)
   
    def get_inventory_recap(self) -> dict:
        """Rekap jumlah barang per status: {'Tersedia': n, 'Dipinjam': n, 'Rusak': n}."""
        rows = self.db.query_all("SELECT status, COUNT(*) AS jumlah FROM items GROUP BY status")
        return {row["status"]: row["jumlah"] for row in rows}

    def get_loan_recap(self) -> dict:
        """Rekap jumlah peminjaman per status_pinjam."""
        rows = self.db.query_all(
            "SELECT status_pinjam, COUNT(*) AS jumlah FROM loans GROUP BY status_pinjam"
        )
        return {row["status_pinjam"]: row["jumlah"] for row in rows}

    def list_loans(self):
        """Daftar peminjaman lengkap dengan id, dipakai buat cari loan_id."""
        return self.db.query_all(
            "SELECT id, user_id, item_id, tanggal_pinjam, tanggal_kembali, status_pinjam "
            "FROM loans ORDER BY id"
        )

    def get_activity_logs(self, user_id: int, limit: int = 50):
        self._require_role(user_id, {ROLE_ADMIN})
        return self.db.query_all(
            "SELECT * FROM activity_logs ORDER BY waktu DESC LIMIT %s", (limit,)
        )


def _ajukan_pinjam(system: InventorySystem, user_id: int):
    """Ajukan pinjam + jelaskan alasan kalau gagal (bukan cuma False)."""
    item_id = int(input("ID barang yang dipinjam: "))
    if system.process_loan_request(user_id, item_id):
        print("Berhasil: pengajuan pinjam dibuat, status Pending.")
        return

    item = system.get_item_status(item_id)
    if not item:
        print(f"Gagal: barang id={item_id} tidak ditemukan.")
    elif item["status"] != "Tersedia":
        print(f"Gagal: barang id={item_id} berstatus '{item['status']}', bukan 'Tersedia'.")
    else:
        print(f"Gagal: barang id={item_id} sudah punya pengajuan pinjam yang belum selesai.")


def _proses_loan(fungsi, system: InventorySystem, user_id: int, kata_kerja: str, status_disyaratkan: str):
    """Approve/reject loan + jelaskan alasan kalau gagal."""
    loan_id = int(input("ID peminjaman (loan_id, lihat menu 3): "))
    if fungsi(user_id, loan_id):
        print(f"Berhasil: peminjaman id={loan_id} {kata_kerja}.")
        return

    loan = system.db.query("SELECT status_pinjam FROM loans WHERE id = %s", (loan_id,))
    if not loan:
        print(f"Gagal: peminjaman id={loan_id} tidak ditemukan.")
    else:
        print(
            f"Gagal: peminjaman id={loan_id} berstatus '{loan['status_pinjam']}', "
            f"harus '{status_disyaratkan}' dulu untuk bisa diproses."
        )


def _kembalikan_barang(system: InventorySystem, user_id: int):
    """Proses pengembalian + jelaskan alasan kalau gagal."""
    loan_id = int(input("ID peminjaman (loan_id, lihat menu 3): "))
    kondisi = input("Kondisi barang (Tersedia/Rusak) [Tersedia]: ") or "Tersedia"
    if system.return_loan(user_id, loan_id, kondisi):
        print(f"Berhasil: peminjaman id={loan_id} dikembalikan, barang jadi '{kondisi}'.")
        return

    loan = system.db.query("SELECT status_pinjam FROM loans WHERE id = %s", (loan_id,))
    if not loan:
        print(f"Gagal: peminjaman id={loan_id} tidak ditemukan.")
    else:
        print(
            f"Gagal: peminjaman id={loan_id} berstatus '{loan['status_pinjam']}', "
            "harus 'Disetujui' dulu sebelum bisa dikembalikan."
        )


def _run_cli():  # pragma: no cover - demo interaktif, tidak dites otomatis
    from db import Database

    db = Database()
    system = InventorySystem(db)

    print("=== Sistem Inventaris Kantor ===")
    user_id = int(input("Masukkan user_id Anda: "))
    user = system._get_user(user_id)
    if not user:
        print("Pengguna tidak ditemukan.")
        return
    print(f"Login sebagai {user['nama']} ({user['role']})")

    aksi = {
        "1": lambda: print(system.search_item()),
        "2": lambda: print(system.get_inventory_recap()),
        "3": lambda: (print(system.get_loan_recap()), print(system.list_loans())),
        "4": lambda: print(system.add_item(
            user_id, input("Kode barang: "), input("Nama barang: ")
        )),
        "5": lambda: _ajukan_pinjam(system, user_id),
        "6": lambda: _proses_loan(system.approve_loan, system, user_id, "disetujui", "Pending"),
        "7": lambda: _proses_loan(system.reject_loan, system, user_id, "ditolak", "Pending"),
        "8": lambda: _kembalikan_barang(system, user_id),
        "9": lambda: print(system.get_activity_logs(user_id)),
    }
    menu_teks = (
        "1) Lihat daftar barang       2) Rekap inventaris        3) Rekap peminjaman\n"
        "4) Tambah barang             5) Ajukan pinjam barang    6) Setujui peminjaman\n"
        "7) Tolak peminjaman          8) Kembalikan barang       9) Log aktivitas (Admin)\n"
        "0) Keluar"
    )

    while True:
        print(menu_teks)
        pilihan = input("Pilih menu: ")
        if pilihan == "0":
            break
        action = aksi.get(pilihan)
        if not action:
            print("Menu tidak dikenal.")
            continue
        try:
            action()
        except (PermissionError, ValueError) as e:
            print(f"Ditolak: {e}")


if __name__ == "__main__":  # pragma: no cover
    _run_cli()
