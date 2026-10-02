@echo off
title Tat demo dieu khien truy xuat dong thoi
cd /d "%~dp0"
echo Dang tat demo (MySQL + ung dung)...
rem Cho MySQL toi da 60 giay de ghi het du lieu xuong dia va tat em (mac dinh chi 10 giay)
docker compose stop -t 60
echo.
echo Da tat. Du lieu MySQL van duoc giu lai, lan sau chay khoi-dong.bat la dung tiep.
timeout /t 4 >nul
