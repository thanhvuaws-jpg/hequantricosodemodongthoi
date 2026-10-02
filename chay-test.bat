@echo off
setlocal
title Chay bo kiem thu - demo dieu khien truy xuat dong thoi
cd /d "%~dp0"

echo ====================================================
echo   CHAY TOAN BO TEST TREN MYSQL THAT (khoang 1 phut)
echo ====================================================
echo   Luu y: khong thao tac tren giao dien web trong luc chay test,
echo   vi test va giao dien dung chung mot co so du lieu.
echo.

docker info >nul 2>&1
if errorlevel 1 (
  echo [LOI] Docker chua chay. Hay mo Docker Desktop ^(hoac chay khoi-dong.bat^) roi chay lai file nay.
  pause
  exit /b 1
)

echo [1/3] Dang bat MySQL va ung dung...
docker compose up -d --build
if errorlevel 1 (
  echo [LOI] Khong khoi dong duoc container. Xem thong bao loi o tren.
  pause
  exit /b 1
)

echo [2/3] Dang cho ung dung ket noi duoc MySQL...
set /a dem=0
:cho_app
"%SystemRoot%\System32\curl.exe" -s -f -o nul http://localhost:8010/api/thong-tin
if not errorlevel 1 goto chay_test
set /a dem+=1
if %dem% geq 60 (
  echo [LOI] Ung dung chua phan hoi sau 2 phut. Xem log bang lenh: docker compose logs app
  pause
  exit /b 1
)
timeout /t 2 /nobreak >nul
goto cho_app

:chay_test
echo [3/3] Dang chay test...
echo.
docker compose exec -T app pytest -q
if errorlevel 1 (
  echo.
  echo [CANH BAO] Co test that bai - xem chi tiet o tren.
) else (
  echo.
  echo Tat ca test deu DAT.
)
echo.
pause
