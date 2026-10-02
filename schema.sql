-- =====================================================================
-- CSDL demo cho de tai: Dieu khien truy xuat dong thoi trong MySQL/InnoDB
-- Nghiep vu: he thong dat ve may bay truc tuyen
-- Moi bang deu dung ENGINE=InnoDB vi chi InnoDB ho tro giao tac va khoa dong
--
-- File nay duoc chay tu dong khi container MySQL khoi tao lan dau, va duoc
-- ung dung chay lai neu phat hien CSDL con dung luoc do cu.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS demo_dongthoi
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE demo_dongthoi;

DROP TABLE IF EXISTS ve;
DROP TABLE IF EXISTS ghe;
DROP TABLE IF EXISTS chuyen_bay;
DROP TABLE IF EXISTS suat_chieu;   -- bang cua phien ban cu (dat ve xem phim)

-- Chuyen bay: giu so ghe con trong - diem tranh chap chinh
CREATE TABLE chuyen_bay (
    ma_chuyen    INT PRIMARY KEY,
    so_hieu      VARCHAR(100)  NOT NULL,             -- vi du: VN-808
    tong_ghe     INT           NOT NULL,
    so_ghe_trong INT           NOT NULL,
    version      INT           NOT NULL DEFAULT 0    -- phuc vu khoa lac quan
) ENGINE=InnoDB;

-- Ve: moi dong la mot ve da ban thanh cong
CREATE TABLE ve (
    ma_ve      INT AUTO_INCREMENT PRIMARY KEY,
    ma_chuyen  INT          NOT NULL,
    hanh_khach VARCHAR(50)  NOT NULL,
    thoi_diem  DATETIME(6)  NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    CONSTRAINT fk_ve_chuyen FOREIGN KEY (ma_chuyen) REFERENCES chuyen_bay(ma_chuyen)
) ENGINE=InnoDB;

-- Ghe: dung cho kich ban deadlock (hai giao tac giu hai ghe theo thu tu nguoc nhau)
CREATE TABLE ghe (
    ma_ghe      INT PRIMARY KEY,
    ma_chuyen   INT          NOT NULL,
    so_ghe      VARCHAR(10)  NOT NULL,                -- vi du: 12A
    trang_thai  VARCHAR(20)  NOT NULL DEFAULT 'trong',
    nguoi_giu   VARCHAR(50)  NULL,
    CONSTRAINT fk_ghe_chuyen FOREIGN KEY (ma_chuyen) REFERENCES chuyen_bay(ma_chuyen)
) ENGINE=InnoDB;
