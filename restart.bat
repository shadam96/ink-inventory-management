@echo off
REM Restart all Docker services

title Ink Inventory Management - Restart Services

echo.
echo Restarting all services...
echo.

cd /d "%~dp0"
docker-compose restart

echo.
echo Services restarted.
echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo Services should be ready now.
echo Frontend: http://localhost:5173
echo API Docs: http://localhost:8000/docs
echo.
pause



