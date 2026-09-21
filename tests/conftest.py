"""Fixture bersama untuk unit test: FakeDatabase (pengganti MySQL sungguhan)."""
import re

import pytest

from app import InventorySystem


class FakeDatabase:
    """Basis data in-memory yang meniru kontrak query/query_all/execute.

    Dipakai supaya unit test tidak butuh koneksi MySQL nyata, tetapi tetap
    memvalidasi SQL persis yang dipanggil oleh InventorySystem.
    """

    def __init__(self):
        self.tables = {"users": [], "items": [], "loans": [], "activity_logs": []}
        self._ids = {"users": 0, "items": 0, "loans": 0, "activity_logs": 0}

    # -- seed helpers ----------------------------------------------------
    def seed_user(self, nama, role):
        self._ids["users"] += 1
        row = {"id": self._ids["users"], "nama": nama, "role": role}
        self.tables["users"].append(row)
        return row["id"]

    def seed_item(self, kode_barang, nama_barang, status="Tersedia"):
        self._ids["items"] += 1
        row = {"id": self._ids["items"], "kode_barang": kode_barang,
               "nama_barang": nama_barang, "status": status}
        self.tables["items"].append(row)
        return row["id"]

    def seed_loan(self, user_id, item_id, status_pinjam="Pending"):
        self._ids["loans"] += 1
        row = {"id": self._ids["loans"], "user_id": user_id, "item_id": item_id,
               "tanggal_pinjam": "2024-01-01", "tanggal_kembali": None,
               "status_pinjam": status_pinjam}
        self.tables["loans"].append(row)
        return row["id"]

    # -- SELECT 
    def query(self, sql, params=()):
        rows = self.query_all(sql, params)
        return rows[0] if rows else None

    def query_all(self, sql, params=()):
        sql_norm = " ".join(sql.split())
        params = tuple(params)

        if sql_norm == "SELECT id, nama, role FROM users WHERE id = %s":
            return [dict(r) for r in self.tables["users"] if r["id"] == params[0]]

        if sql_norm == "SELECT id FROM items WHERE kode_barang = %s":
            return [{"id": r["id"]} for r in self.tables["items"] if r["kode_barang"] == params[0]]

        if sql_norm == "SELECT id FROM items WHERE id = %s":
            return [{"id": r["id"]} for r in self.tables["items"] if r["id"] == params[0]]

        if sql_norm == "SELECT status FROM items WHERE id = %s":
            return [{"status": r["status"]} for r in self.tables["items"] if r["id"] == params[0]]

        if sql_norm == "SELECT id FROM loans WHERE item_id = %s AND status_pinjam IN ('Pending', 'Disetujui')":
            return [{"id": r["id"]} for r in self.tables["loans"]
                    if r["item_id"] == params[0] and r["status_pinjam"] in ("Pending", "Disetujui")]

        if sql_norm == "SELECT item_id, status_pinjam FROM loans WHERE id = %s":
            return [{"item_id": r["item_id"], "status_pinjam": r["status_pinjam"]}
                    for r in self.tables["loans"] if r["id"] == params[0]]

        if sql_norm == "SELECT status_pinjam FROM loans WHERE id = %s":
            return [{"status_pinjam": r["status_pinjam"]} for r in self.tables["loans"] if r["id"] == params[0]]

        if sql_norm == "SELECT id, kode_barang, nama_barang, status FROM items WHERE status = %s":
            return [dict(r) for r in self.tables["items"] if r["status"] == params[0]]

        if sql_norm == "SELECT status, COUNT(*) AS jumlah FROM items GROUP BY status":
            return self._group_count(self.tables["items"], "status")

        if sql_norm == "SELECT status_pinjam, COUNT(*) AS jumlah FROM loans GROUP BY status_pinjam":
            return self._group_count(self.tables["loans"], "status_pinjam")

        if sql_norm == "SELECT id, user_id, item_id, tanggal_pinjam, tanggal_kembali, status_pinjam FROM loans ORDER BY id":
            return [dict(r) for r in sorted(self.tables["loans"], key=lambda r: r["id"])]

        if sql_norm == "SELECT * FROM activity_logs ORDER BY waktu DESC LIMIT %s":
            return list(reversed(self.tables["activity_logs"]))[: params[0]]

        if sql_norm.startswith("SELECT id, kode_barang, nama_barang, status FROM items WHERE 1=1"):
            return self._search_items(sql_norm, params)

        raise NotImplementedError(f"Query tidak dikenali fake db: {sql_norm}")

    def _search_items(self, sql_norm, params):
        rows = list(self.tables["items"])
        idx = 0
        if "nama_barang LIKE %s OR kode_barang LIKE %s" in sql_norm:
            like = params[idx].strip("%").lower()
            idx += 2
            rows = [r for r in rows if like in r["nama_barang"].lower() or like in r["kode_barang"].lower()]
        if sql_norm.endswith("AND status = %s"):
            status = params[idx]
            rows = [r for r in rows if r["status"] == status]
        return [dict(r) for r in rows]

    @staticmethod
    def _group_count(rows, field):
        counts = {}
        for row in rows:
            counts[row[field]] = counts.get(row[field], 0) + 1
        return [{field: k, "jumlah": v} for k, v in counts.items()]

    # -- INSERT/UPDATE/DELETE 
    def execute(self, sql, params=()):
        sql_norm = " ".join(sql.split())
        params = list(params)

        m = re.match(r"INSERT INTO (\w+) \((.+?)\) VALUES \((.+?)\)$", sql_norm)
        if m:
            return self._insert(m.group(1), m.group(2), m.group(3), params)

        m = re.match(r"UPDATE (\w+) SET (.+) WHERE id = %s$", sql_norm)
        if m:
            return self._update(m.group(1), m.group(2), params)

        m = re.match(r"DELETE FROM (\w+) WHERE id = %s$", sql_norm)
        if m:
            return self._delete(m.group(1), params[0])

        raise NotImplementedError(f"Statement tidak dikenali fake db: {sql_norm}")

    def _insert(self, table, columns_expr, values_expr, params):
        columns = [c.strip() for c in columns_expr.split(",")]
        values = [v.strip() for v in values_expr.split(",")]
        param_iter = iter(params)
        row = {}
        for col, val in zip(columns, values):
            if val == "%s":
                row[col] = next(param_iter)
            elif val == "CURDATE()":
                row[col] = "2024-01-01"
            else:
                row[col] = val.strip("'")
        if table == "items":
            row.setdefault("status", "Tersedia")
        if table == "loans":
            row.setdefault("tanggal_kembali", None)
        self._ids[table] += 1
        row["id"] = self._ids[table]
        self.tables[table].append(row)
        return row["id"]

    def _update(self, table, set_expr, params):
        assignments = [a.strip() for a in set_expr.split(",")]
        row_id = params[-1]
        param_iter = iter(params[:-1])
        updates = {}
        for assignment in assignments:
            col, val = [p.strip() for p in assignment.split("=", 1)]
            if val == "%s":
                updates[col] = next(param_iter)
            elif val == "CURDATE()":
                updates[col] = "2024-01-01"
            else:
                updates[col] = val.strip("'")
        for row in self.tables[table]:
            if row["id"] == row_id:
                row.update(updates)
                return 1
        return 0

    def _delete(self, table, row_id):
        before = len(self.tables[table])
        self.tables[table] = [r for r in self.tables[table] if r["id"] != row_id]
        return before - len(self.tables[table])


@pytest.fixture
def fake_db():
    db = FakeDatabase()
    return db


@pytest.fixture
def seeded_db(fake_db):
    """DB terisi 1 Staf, 1 Petugas, 1 Admin, dan 2 barang."""
    fake_db.seed_user("Andi", "Staf")       # id=1
    fake_db.seed_user("Budi", "Petugas")    # id=2
    fake_db.seed_user("Citra", "Admin")     # id=3
    fake_db.seed_item("INV-001", "Laptop Dell", "Tersedia")  # id=1
    fake_db.seed_item("INV-002", "Proyektor Epson", "Rusak")  # id=2
    return fake_db


@pytest.fixture
def system(seeded_db):
    return InventorySystem(seeded_db)
