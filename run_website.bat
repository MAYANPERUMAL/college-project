@echo off
setlocal
title Tech Mart - Local Development Server
cd /d "%~dp0"

set "PY_EXE=C:\Users\K.MAYANPERUMAL\AppData\Local\Python\bin\python.exe"
if not exist "%PY_EXE%" set "PY_EXE=python"

echo =====================================================================
echo           Starting Tech Mart E-Commerce Server
echo =====================================================================
echo.
echo Website Entry URL (Login): http://127.0.0.1:8000/
echo Customer Storefront URL:    http://127.0.0.1:8000/home/
echo Custom Admin Portal:        http://127.0.0.1:8000/admin-dashboard/
echo Django Built-in Admin:      http://127.0.0.1:8000/django-admin/
echo.
echo Pre-Configured Credentials:
echo   • Admin:    admin / admin123
echo   • Customer: rahul / customer123
echo.
"%PY_EXE%" manage.py runserver 127.0.0.1:8000
pause
