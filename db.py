
import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import pooling


class Database:
    """Wrapper akses basis data MySQL."""

    def __init__(self, host=None, user=None, password=None, database=None,
                 port=None, pool_name="inventaris_pool", pool_size=5):
        self._config = {
            "host": host or os.getenv("DB_HOST", "localhost"),
            "user": user or os.getenv("DB_USER", "root"),
            "password": password if password is not None else os.getenv("DB_PASSWORD", ""),
            "database": database or os.getenv("DB_NAME", "inventaris_kantor"),
            "port": int(port or os.getenv("DB_PORT", 3306)),
        }
        self._pool = pooling.MySQLConnectionPool(
            pool_name=pool_name,
            pool_size=pool_size,
            **self._config,
        )

    @contextmanager
    def _cursor(self):
        conn = self._pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            yield conn, cursor
        finally:
            cursor.close()
            conn.close()

    def query(self, sql: str, params: tuple = ()):
        """Jalankan SELECT, kembalikan baris pertama sebagai dict atau None."""
        with self._cursor() as (_, cursor):
            cursor.execute(sql, params)
            return cursor.fetchone()

    def query_all(self, sql: str, params: tuple = ()):
        """Jalankan SELECT, kembalikan seluruh baris sebagai list of dict."""
        with self._cursor() as (_, cursor):
            cursor.execute(sql, params)
            return cursor.fetchall()

    def execute(self, sql: str, params: tuple = ()):
        """Jalankan INSERT/UPDATE/DELETE lalu commit, kembalikan lastrowid/rowcount."""
        with self._cursor() as (conn, cursor):
            cursor.execute(sql, params)
            conn.commit()
            return cursor.lastrowid or cursor.rowcount
