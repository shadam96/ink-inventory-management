@echo off
REM Ink Inventory Management System - Quick Start Batch File
REM This file launches the PowerShell setup script

title Ink Inventory Management - Quick Start
color 0A

echo.
echo ========================================
echo   Ink Inventory Management System
echo   Quick Start Setup
echo ========================================
echo.
echo This will:
echo   1. Check Docker Desktop is running
echo   2. Start all services
echo   3. Initialize the database
echo   4. Create admin user
echo   5. Open the application
echo.
echo Please wait, this may take 2-5 minutes...
echo.

REM Check if PowerShell is available
powershell -Command "exit 0" >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ERROR: PowerShell is not available!
    echo Please install PowerShell or use Windows 10/11
    echo.
    pause
    exit /b 1
)

REM Get the directory where this batch file is located
set "SCRIPT_DIR=%~dp0"

REM Change to script directory
cd /d "%SCRIPT_DIR%"

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0setup.ps1"

if errorlevel 1 (
    color 0C
    echo.
    echo ========================================
    echo   Setup encountered errors!
    echo ========================================
    echo.
    echo Check setup.log for details: %SCRIPT_DIR%setup.log
    echo.
    echo Common issues:
    echo   - Docker Desktop not running
    echo   - Ports 5173 or 8000 already in use
    echo   - Insufficient disk space
    echo.
    pause
    exit /b 1
)

color 0A
echo.
echo ========================================
echo   Setup completed successfully!
echo ========================================
echo.
pause

