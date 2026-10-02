"""Cấu hình chung cho bộ kiểm thử.

Các test chạy trên MySQL THẬT (container demo_dongthoi_mysql), vì thứ cần
kiểm chứng chính là hành vi khóa và mức cô lập của InnoDB – thứ không thể
giả lập bằng mock.

Lưu ý: đừng dùng giao diện web trong lúc chạy test, vì hai bên dùng chung
một cơ sở dữ liệu.
"""
import pytest

from app import csdl


@pytest.fixture(scope="session", autouse=True)
def can_mysql():
    try:
        conn = csdl.ket_noi()
        conn.close()
        csdl.dam_bao_luoc_do()
    except Exception as e:  # noqa: BLE001
        pytest.exit(
            f"Không kết nối được MySQL tại {csdl.CAU_HINH['host']}:{csdl.CAU_HINH['port']} – "
            f"hãy chạy 'docker compose up -d' trước. Chi tiết: {e}",
            returncode=2,
        )
