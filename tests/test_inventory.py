"""
Unit test untuk InventorySystem (app.py).
Menggunakan FakeDatabase (tests/conftest.py) sehingga tidak butuh MySQL nyata.

ID pengguna hasil seed (lihat conftest.seeded_db):
  1 = Andi   (Staf)
  2 = Budi   (Petugas)
  3 = Citra  (Admin)
ID barang:
  1 = INV-001 Laptop Dell   (Tersedia)
  2 = INV-002 Proyektor     (Rusak)
"""
import pytest



# Peminjaman Barang

class TestProcessLoanRequest:
    def test_berhasil_saat_barang_tersedia(self, system):
        assert system.process_loan_request(user_id=1, item_id=1) is True
        loan = system.db.query("SELECT item_id, status_pinjam FROM loans WHERE id = %s", (1,))
        assert loan == {"item_id": 1, "status_pinjam": "Pending"}

    def test_gagal_saat_barang_rusak(self, system):
        assert system.process_loan_request(user_id=1, item_id=2) is False

    def test_gagal_saat_barang_tidak_ditemukan(self, system):
        assert system.process_loan_request(user_id=1, item_id=999) is False

    def test_gagal_jika_sudah_ada_pengajuan_pending(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        assert system.process_loan_request(user_id=1, item_id=1) is False

    def test_user_tidak_dikenal_raise_value_error(self, system):
        with pytest.raises(ValueError):
            system.process_loan_request(user_id=999, item_id=1)


class TestApproveRejectReturnLoan:
    def test_approve_mengubah_status_loan_dan_item(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        assert system.approve_loan(user_id=2, loan_id=1) is True
        assert system.get_item_status(1) == {"status": "Dipinjam"}

    def test_approve_oleh_staf_ditolak_permission_error(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        with pytest.raises(PermissionError):
            system.approve_loan(user_id=1, loan_id=1)

    def test_approve_loan_bukan_pending_return_false(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        system.approve_loan(user_id=2, loan_id=1)
        assert system.approve_loan(user_id=2, loan_id=1) is False

    def test_reject_mengubah_status_ditolak(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        assert system.reject_loan(user_id=2, loan_id=1) is True
        loan = system.db.query("SELECT status_pinjam FROM loans WHERE id = %s", (1,))
        assert loan["status_pinjam"] == "Ditolak"

    def test_return_loan_mengembalikan_item_ke_tersedia(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        system.approve_loan(user_id=2, loan_id=1)
        assert system.return_loan(user_id=2, loan_id=1) is True
        assert system.get_item_status(1) == {"status": "Tersedia"}

    def test_return_loan_dengan_kondisi_rusak(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        system.approve_loan(user_id=2, loan_id=1)
        system.return_loan(user_id=2, loan_id=1, kondisi="Rusak")
        assert system.get_item_status(1) == {"status": "Rusak"}

    def test_return_loan_kondisi_invalid_raise(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        system.approve_loan(user_id=2, loan_id=1)
        with pytest.raises(ValueError):
            system.return_loan(user_id=2, loan_id=1, kondisi="Hilang")



# Manajemen Barang

class TestManajemenBarang:
    def test_petugas_bisa_tambah_barang(self, system):
        new_id = system.add_item(user_id=2, kode_barang="INV-003", nama_barang="Meja")
        assert new_id == 3
        assert system.search_item(keyword="Meja") == [
            {"id": 3, "kode_barang": "INV-003", "nama_barang": "Meja", "status": "Tersedia"}
        ]

    def test_staf_tidak_bisa_tambah_barang(self, system):
        with pytest.raises(PermissionError):
            system.add_item(user_id=1, kode_barang="INV-003", nama_barang="Meja")

    def test_kode_barang_duplikat_raise(self, system):
        with pytest.raises(ValueError):
            system.add_item(user_id=2, kode_barang="INV-001", nama_barang="Laptop Lain")

    def test_edit_item_mengubah_nama_dan_status(self, system):
        assert system.edit_item(user_id=2, item_id=2, nama_barang="Proyektor Baru", status="Tersedia") is True
        item = system.search_item(keyword="Proyektor Baru")[0]
        assert item["status"] == "Tersedia"

    def test_edit_item_status_invalid_raise(self, system):
        with pytest.raises(ValueError):
            system.edit_item(user_id=2, item_id=2, status="Hilang")

    def test_edit_item_tidak_ditemukan_return_false(self, system):
        assert system.edit_item(user_id=2, item_id=999, nama_barang="X") is False

    def test_delete_item_berhasil(self, system):
        assert system.delete_item(user_id=2, item_id=2) is True
        assert system.search_item(keyword="Proyektor") == []

    def test_delete_item_yang_sedang_dipinjam_raise(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        system.approve_loan(user_id=2, loan_id=1)
        with pytest.raises(ValueError):
            system.delete_item(user_id=2, item_id=1)

    def test_search_item_by_status(self, system):
        hasil = system.search_item(status="Rusak")
        assert [r["kode_barang"] for r in hasil] == ["INV-002"]



# Laporan & Log Aktivitas

class TestLaporan:
    def test_get_inventory_recap(self, system):
        recap = system.get_inventory_recap()
        assert recap == {"Tersedia": 1, "Rusak": 1}

    def test_get_loan_recap(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        assert system.get_loan_recap() == {"Pending": 1}

    def test_list_loans_tampilkan_loan_id(self, system):
        system.process_loan_request(user_id=1, item_id=1)
        hasil = system.list_loans()
        assert hasil == [
            {"id": 1, "user_id": 1, "item_id": 1, "tanggal_pinjam": "2024-01-01",
             "tanggal_kembali": None, "status_pinjam": "Pending"}
        ]

    def test_get_activity_logs_hanya_admin(self, system):
        system.add_item(user_id=2, kode_barang="INV-003", nama_barang="Meja")
        logs = system.get_activity_logs(user_id=3)
        assert len(logs) == 1
        assert logs[0]["aksi"] == "TAMBAH_BARANG"

    def test_get_activity_logs_ditolak_untuk_petugas(self, system):
        with pytest.raises(PermissionError):
            system.get_activity_logs(user_id=2)
