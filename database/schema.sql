-- Tabel User
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama VARCHAR(100) NOT NULL,
    role ENUM('Staf', 'Petugas', 'Admin') NOT NULL
);

-- Tabel Barang
CREATE TABLE items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    kode_barang VARCHAR(20) UNIQUE NOT NULL,
    nama_barang VARCHAR(100) NOT NULL,
    status ENUM('Tersedia', 'Dipinjam', 'Rusak') DEFAULT 'Tersedia',
    INDEX idx_status (status) -- Optimasi Skalabilitas
);

-- Tabel Peminjaman
CREATE TABLE loans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    item_id INT,
    tanggal_pinjam DATE NOT NULL,
    tanggal_kembali DATE NULL,
    status_pinjam ENUM('Pending', 'Disetujui', 'Ditolak', 'Dikembalikan') DEFAULT 'Pending',
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (item_id) REFERENCES items(id),
    INDEX idx_status_pinjam (status_pinjam)
);

-- Tabel Log Aktivitas (dipakai Admin untuk audit)
CREATE TABLE activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    aksi VARCHAR(50) NOT NULL,
    keterangan VARCHAR(255) NULL,
    waktu DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_waktu (waktu)
);