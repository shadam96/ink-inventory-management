@echo off
REM Stop all Docker services

title Ink Inventory Management - Stop Services

echo.
echo Stopping all services...
echo.

cd /d "%~dp0"
docker-compose down

echo.
echo Services stopped.
echo.
pause



