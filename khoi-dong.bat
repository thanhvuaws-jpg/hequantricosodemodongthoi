@echo off
setlocal
title Demo dieu khien truy xuat dong thoi - MySQL/InnoDB
cd /d "%~dp0"

echo ====================================================
echo   DEMO DIEU KHIEN TRUY XUAT DONG THOI - MySQL/InnoDB
echo ====================================================
echo.

where docker >nul 2>&1
if errorlevel 1 (
  echo [LOI] Khong tim thay Docker. Hay cai Docker Desktop truoc.
  pause
  exit /b 1
)

rem ---------- 1. Bao dam Docker dang chay ----------
docker info >nul 2>&1
if not errorlevel 1 goto docker_san_sang

echo [1/3] Docker chua chay, dang mo Docker Desktop...
if not exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
  echo [LOI] Khong tim thay Docker Desktop. Hay tu mo Docker Desktop roi chay lai file nay.
  pause
  exit /b 1
)
start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
set /a dem=0
:cho_docker
timeout /t 3 /nobreak >nul
docker info >nul 2>&1
if not errorlevel 1 goto docker_san_sang
set /a dem+=1
if %dem% geq 60 (
  echo [LOI] Docker khoi dong qua lau ^(hon 3 phut^).
  pause
  exit /b 1
)
echo       ...dang cho Docker khoi dong
goto cho_docker

:docker_san_sang
echo [1/3] Docker da san sang.

rem ---------- 2. Khoi dong MySQL + ung dung ----------
echo [2/3] Dang khoi dong MySQL va ung dung (lan dau co the mat vai phut)...
docker compose up -d --build
if errorlevel 1 (
  echo [LOI] Khong khoi dong duoc container. Xem thong bao loi o tren.
  pause
  exit /b 1
)

rem ---------- 3. Cho ung dung va MySQL san sang roi mo trinh duyet ----------
echo [3/3] Dang cho ung dung ket noi duoc MySQL...
set /a dem=0
:cho_app
"%SystemRoot%\System32\curl.exe" -s -f -o nul http://localhost:8010/api/thong-tin
if not errorlevel 1 goto xong
set /a dem+=1
if %dem% geq 60 (
  echo [LOI] Ung dung chua phan hoi sau 2 phut. Xem log bang lenh: docker compose logs app
  pause
  exit /b 1
)
timeout /t 2 /nobreak >nul
goto cho_app

:xong
echo.
echo   Da san sang: http://localhost:8010
echo   Muon tat demo: chay file dung.bat
echo.
start "" http://localhost:8010
timeout /t 5 >nul
