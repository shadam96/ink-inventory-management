# Quick Start Guide - Ink Inventory Management System

## For Non-Technical Users

This guide will help you set up and run the inventory management system with just a few clicks.

## Prerequisites

Before you start, make sure you have:

1. **Docker Desktop** installed and running
   - Download from: https://www.docker.com/products/docker-desktop
   - After installation, start Docker Desktop
   - Wait until Docker Desktop shows "Docker is running" (green icon in system tray)

2. **Windows 10 or 11** (PowerShell is included)

## Quick Start (One-Click Setup)

### Option 1: Double-Click Setup (Recommended)

1. **Double-click** `start.bat` file
2. Wait for the script to complete (2-5 minutes)
3. The application will open automatically in your browser

That's it! The system is now running.

### Option 2: Manual Steps

If the batch file doesn't work, you can run these commands manually:

1. Open PowerShell in the project folder
2. Run: `.\setup.ps1`
3. Wait for completion
4. Open browser to: http://localhost:5173

## What the Setup Script Does

The setup script automatically:

1. ✅ Checks if Docker is running
2. ✅ Starts all required services (database, backend, frontend)
3. ✅ Initializes the database
4. ✅ Creates an admin user
5. ✅ Opens the application in your browser

## Accessing the Application

After setup completes, you can access:

- **Main Application**: http://localhost:5173
- **API Documentation**: http://localhost:8000/docs

## Login Credentials

- **Username**: `admin`
- **Password**: `admin123456`

⚠️ **Important**: Change this password after first login!

## Useful Commands

### Stop the Application

Double-click `stop.bat` to stop all services.

### Restart the Application

Double-click `restart.bat` to restart all services.

### View Logs

If something goes wrong, check the `setup.log` file in the project folder.

## Troubleshooting

### "Docker is not running"

**Solution**: 
1. Open Docker Desktop
2. Wait for it to start (green icon in system tray)
3. Run `start.bat` again

### "Port already in use"

**Solution**: 
1. Stop other applications using ports 5173 or 8000
2. Or restart your computer
3. Run `start.bat` again

### "Services won't start"

**Solution**:
1. Check Docker Desktop is running
2. Open PowerShell in project folder
3. Run: `docker-compose logs`
4. Check the error messages
5. Contact support with the error details

### "Can't access http://localhost:5173"

**Solution**:
1. Wait 1-2 minutes for services to fully start
2. Check if Docker containers are running: `docker ps`
3. Try refreshing the browser
4. Check firewall settings

### "Admin user creation failed"

**Solution**:
1. The user might already exist - try logging in
2. If login fails, check backend logs: `docker-compose logs backend`
3. You can create users manually via the API at http://localhost:8000/docs

## Getting Help

If you encounter issues:

1. Check `setup.log` file for detailed error messages
2. Check Docker Desktop logs
3. Contact your technical support with:
   - Screenshot of the error
   - Contents of `setup.log`
   - Docker Desktop status

## Next Steps

After successful setup:

1. ✅ Login with admin credentials
2. ✅ Create your first inventory item
3. ✅ Add customers
4. ✅ Start receiving goods
5. ✅ Test the barcode scanner (requires camera permissions)

## System Requirements

- **Windows**: 10 or 11
- **RAM**: Minimum 4GB (8GB recommended)
- **Disk Space**: 2GB free space
- **Docker Desktop**: Latest version
- **Internet**: Required for initial Docker image downloads

---

**Need Help?** Contact your system administrator or technical support.



