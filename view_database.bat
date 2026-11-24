@echo off
setlocal
title Tech Mart - MySQL Database Inspector
cd /d "%~dp0"

set "PY_EXE=C:\Users\K.MAYANPERUMAL\AppData\Local\Python\bin\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=python"

echo Checking MySQL Database Connection...
echo.
"%PY_EXE%" inspect_db.py
echo.
pause
