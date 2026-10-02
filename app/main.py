"""API cho ứng dụng demo điều khiển truy xuất đồng thời."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import csdl, kichban, phongthinghiem, xungdot

THU_MUC_TINH = Path(__file__).parent / "static"


@asynccontextmanager
async def vong_doi(_: FastAPI):
    try:
        csdl.dam_bao_luoc_do()
    except Exception:  # noqa: BLE001 – MySQL chưa sẵn sàng; /api/thong-tin sẽ thử lại
        pass
    yield


app = FastAPI(title="Demo điều khiển truy xuất đồng thời – MySQL/InnoDB", lifespan=vong_doi)


@app.middleware("http")
async def luon_kiem_tra_ban_moi(request: Request, call_next):
    """Bắt trình duyệt hỏi lại máy chủ mỗi lần tải giao diện (trả 304 nếu tệp chưa đổi).
    Nếu không, trình duyệt có thể giữ bản JS/CSS cũ sau khi giao diện được cập nhật."""
    phan_hoi = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        phan_hoi.headers["Cache-Control"] = "no-cache"
    return phan_hoi
app.mount("/static", StaticFiles(directory=THU_MUC_TINH), name="static")


@app.exception_handler(csdl.DangBan)
def _dang_ban(_: Request, e: csdl.DangBan):
    return JSONResponse(status_code=409, content={"detail": str(e)})


@app.exception_handler(ValueError)
def _sai_tham_so(_: Request, e: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(e)})


class YeuCauChay(BaseModel):
    che_do: str = "khong_khoa"
    so_khach: int = Field(default=10, ge=1, le=60)
    ton_kho: int = Field(default=5, ge=1, le=500)
    think_ms: int = Field(default=80, ge=0, le=2000)
    muc_co_lap: str | None = None


class YeuCauDatLai(BaseModel):
    ton_kho: int = Field(default=5, ge=1, le=500)


class YeuCauSoSanh(BaseModel):
    so_khach: int = Field(default=10, ge=1, le=60)
    ton_kho: int = Field(default=5, ge=1, le=500)
    think_ms: int = Field(default=80, ge=0, le=2000)
    so_lan: int = Field(default=3, ge=1, le=10)
    muc_co_lap: str | None = None


class YeuCauKhaoSat(BaseModel):
    cac_muc: list[int] = Field(default=[5, 10, 20, 40], min_length=1, max_length=6)
    think_ms: int = Field(default=50, ge=0, le=500)


class YeuCauThiNghiem(BaseModel):
    ma: str
    muc_co_lap: str


class YeuCauXungDot(BaseModel):
    ma: str
    loai: str


@app.get("/")
def trang_chu():
    return FileResponse(THU_MUC_TINH / "index.html")


@app.get("/api/thong-tin")
def thong_tin():
    try:
        csdl.dam_bao_luoc_do()
        may_chu = csdl.thong_tin_may_chu()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Không kết nối được MySQL: {e}")
    return {"may_chu": may_chu, "che_do": kichban.CHE_DO,
            "muc_co_lap": list(csdl.MUC_CO_LAP_HOP_LE)}


@app.get("/api/trang-thai")
def trang_thai():
    return kichban.trang_thai_hien_tai()


@app.post("/api/dat-lai")
def dat_lai(yc: YeuCauDatLai):
    with csdl.giu_quyen_chay():
        kichban.dat_lai_du_lieu(yc.ton_kho)
        return kichban.trang_thai_hien_tai()


@app.post("/api/chay")
def chay(yc: YeuCauChay):
    with csdl.giu_quyen_chay():
        return kichban.chay_kich_ban(
            che_do=yc.che_do, so_khach=yc.so_khach, ton_kho=yc.ton_kho,
            think_ms=yc.think_ms, muc_co_lap=yc.muc_co_lap,
        )


@app.post("/api/so-sanh")
def so_sanh(yc: YeuCauSoSanh):
    with csdl.giu_quyen_chay():
        return kichban.so_sanh_che_do(yc.so_khach, yc.ton_kho, yc.think_ms,
                                      yc.so_lan, yc.muc_co_lap)


@app.post("/api/khao-sat")
def khao_sat(yc: YeuCauKhaoSat):
    with csdl.giu_quyen_chay():
        return kichban.khao_sat_theo_so_khach(yc.cac_muc, yc.think_ms)


@app.get("/api/thi-nghiem")
def ds_thi_nghiem():
    return {"thi_nghiem": phongthinghiem.danh_sach_thi_nghiem(),
            "cac_muc": list(phongthinghiem.CAC_MUC),
            "du_lieu_ban_dau": phongthinghiem.DU_LIEU_BAN_DAU}


@app.post("/api/thi-nghiem/chay")
def chay_thi_nghiem(yc: YeuCauThiNghiem):
    with csdl.giu_quyen_chay():
        return phongthinghiem.chay_thi_nghiem(yc.ma, yc.muc_co_lap)


@app.post("/api/thi-nghiem/ma-tran")
def ma_tran():
    with csdl.giu_quyen_chay():
        return phongthinghiem.chay_ma_tran()


@app.get("/api/xung-dot")
def ds_xung_dot():
    return {"xung_dot": xungdot.danh_sach_xung_dot(),
            "du_lieu_ban_dau": phongthinghiem.DU_LIEU_BAN_DAU}


@app.post("/api/xung-dot/chay")
def chay_xung_dot(yc: YeuCauXungDot):
    with csdl.giu_quyen_chay():
        return xungdot.chay_xung_dot(yc.ma, yc.loai)
