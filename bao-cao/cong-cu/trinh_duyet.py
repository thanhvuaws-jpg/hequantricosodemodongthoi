"""Điều khiển Chrome chạy ngầm qua DevTools Protocol để chụp ảnh giao diện ứng dụng demo."""
import base64
import json
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


class Chrome:
    def __init__(self, rong=1440, cao=900, ti_le=1.5, cong=9344):
        self.rong, self.cao, self.ti_le = rong, cao, ti_le
        self.thu_muc = tempfile.mkdtemp(prefix="chrome-baocao-")
        self.p = subprocess.Popen([
            CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            f"--remote-debugging-port={cong}", "--remote-allow-origins=*",
            f"--user-data-dir={self.thu_muc}", f"--window-size={rong},{cao}", "about:blank",
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{cong}/json"))
                trang = next(t for t in tabs if t["type"] == "page")
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.2)
        else:
            raise RuntimeError("Không mở được Chrome")
        self.ws = websocket.create_connection(trang["webSocketDebuggerUrl"], timeout=120)
        self.dem = 0
        self.loi_console = []
        self.phan_hoi = []   # (url, requestId) của các phản hồi mạng, để đọc lại JSON của API
        self.gui("Page.enable")
        self.gui("Runtime.enable")
        self.gui("Network.enable", maxTotalBufferSize=200_000_000, maxResourceBufferSize=50_000_000)
        self.kich_thuoc(rong, cao, ti_le)

    def gui(self, phuong_thuc, **thamso):
        self.dem += 1
        ma = self.dem
        self.ws.send(json.dumps({"id": ma, "method": phuong_thuc, "params": thamso}))
        while True:
            tin = json.loads(self.ws.recv())
            if tin.get("method") == "Runtime.exceptionThrown":
                self.loi_console.append(tin["params"]["exceptionDetails"].get("text"))
            if tin.get("method") == "Runtime.consoleAPICalled" and tin["params"]["type"] == "error":
                self.loi_console.append(" ".join(str(a.get("value", a.get("description")))
                                                 for a in tin["params"]["args"]))
            if tin.get("method") == "Network.responseReceived":
                self.phan_hoi.append((tin["params"]["response"]["url"], tin["params"]["requestId"]))
            if tin.get("id") == ma:
                if "error" in tin:
                    raise RuntimeError(f"{phuong_thuc}: {tin['error']}")
                return tin.get("result", {})

    def js(self, bieu_thuc):
        kq = self.gui("Runtime.evaluate", expression=bieu_thuc, returnByValue=True, awaitPromise=True)
        if "exceptionDetails" in kq:
            raise RuntimeError(f"Lỗi JS: {kq['exceptionDetails']}")
        return kq["result"].get("value")

    def cho(self, bieu_thuc, toi_da=60.0):
        han = time.time() + toi_da
        while time.time() < han:
            try:
                if self.js(bieu_thuc):
                    return
            except RuntimeError:
                pass
            time.sleep(0.2)
        raise RuntimeError(f"Hết giờ chờ: {bieu_thuc}")

    def lay_json(self, duoi_url):
        """Nội dung JSON của phản hồi gần nhất có URL kết thúc bằng duoi_url."""
        import json as _json
        self.js("1")   # đọc hết các sự kiện mạng đang chờ trong hàng đợi
        for url, ma in reversed(self.phan_hoi):
            if url.split("?")[0].endswith(duoi_url):
                kq = self.gui("Network.getResponseBody", requestId=ma)
                than = kq["body"]
                if kq.get("base64Encoded"):
                    than = base64.b64decode(than).decode("utf-8")
                return _json.loads(than)
        raise RuntimeError(f"Không thấy phản hồi {duoi_url}")

    def mo(self, url):
        self.gui("Page.navigate", url=url)
        time.sleep(0.4)
        self.cho("document.readyState === 'complete'")
        time.sleep(0.8)

    def kich_thuoc(self, rong, cao, ti_le):
        self.rong, self.cao, self.ti_le = rong, cao, ti_le
        self.gui("Emulation.setDeviceMetricsOverride", width=rong, height=cao, deviceScaleFactor=ti_le,
                 mobile=False)

    def chup(self, tep, x=0, y=0, w=None, h=None):
        w = w or self.rong
        h = h or self.cao
        kq = self.gui("Page.captureScreenshot", format="png", captureBeyondViewport=True,
                      clip={"x": x, "y": y, "width": w, "height": h, "scale": 1})
        Path(tep).parent.mkdir(parents=True, exist_ok=True)
        Path(tep).write_bytes(base64.b64decode(kq["data"]))
        return Path(tep)

    def chup_khung(self, tep):
        """Chụp đúng phần đang hiển thị trên màn hình (giữ nguyên vị trí cuộn và phần tử dính)."""
        kq = self.gui("Page.captureScreenshot", format="png")
        Path(tep).parent.mkdir(parents=True, exist_ok=True)
        Path(tep).write_bytes(base64.b64decode(kq["data"]))
        return Path(tep)

    def vung(self, selector, le=0):
        """Toạ độ (theo trang) của một phần tử, kèm lề."""
        return self.js(f"""(() => {{
            const e = document.querySelector({json.dumps(selector)});
            if (!e) return null;
            const r = e.getBoundingClientRect();
            return {{x: r.left + window.scrollX - {le}, y: r.top + window.scrollY - {le},
                     w: r.width + 2 * {le}, h: r.height + 2 * {le}}};
        }})()""")

    def chup_phan_tu(self, tep, selector, le=8):
        v = self.vung(selector, le)
        if not v:
            raise RuntimeError(f"Không thấy {selector}")
        return self.chup(tep, max(0, v["x"]), max(0, v["y"]), v["w"], v["h"])

    def dong(self):
        try:
            self.ws.close()
        finally:
            self.p.terminate()
