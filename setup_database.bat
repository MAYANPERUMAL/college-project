@echo off
setlocal
title Tech Mart - Setup MySQL Database
cd /d "%~dp0"

set "PY_EXE=C:\Users\K.MAYANPERUMAL\AppData\Local\Python\bin\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=python"

echo =====================================================================
echo           Tech Mart - E-Commerce MySQL Database Setup
echo =====================================================================
echo.
"%PY_EXE%" setup_mysql.py
pause
