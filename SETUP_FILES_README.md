# Setup Files Created for Easy Deployment

This document explains the setup files created to help non-technical users get started quickly.

## 📁 Files Created

### Main Setup Files

1. **`start.bat`** ⭐ **START HERE**
   - Double-click to run the entire setup
   - Checks Docker, starts services, initializes database, creates admin user
   - Opens browser automatically when done

2. **`setup.ps1`**
   - PowerShell script that does all the work
   - Called by `start.bat`
   - Can be run directly: `powershell -ExecutionPolicy Bypass -File setup.ps1`

3. **`stop.bat`**
   - Stops all Docker services
   - Use when you're done testing

4. **`restart.bat`**
   - Restarts all services
   - Useful if something stops working

### Documentation Files

5. **`QUICK_START_GUIDE.md`**
   - Step-by-step guide for non-technical users
   - Troubleshooting section
   - Common issues and solutions

6. **`README_SETUP.md`**
   - Quick reference for setup
   - Points to important files

7. **`CREATE_EXECUTABLE.md`**
   - Instructions for creating a Windows .exe file
   - Multiple methods explained

8. **`create-exe.ps1`**
   - Script to convert `setup.ps1` to `.exe`
   - Requires PS2EXE module

### Log Files (Generated)

9. **`setup.log`**
   - Created automatically when setup runs
   - Contains detailed logs of all operations
   - Useful for troubleshooting

## 🚀 Quick Start for End User

1. Install Docker Desktop
2. Double-click `start.bat`
3. Wait for completion
4. Login at http://localhost:5173

## 🔧 For Developers

### Testing the Setup Script

```powershell
# Test the setup script
cd "C:\Users\Adam Shacham\Lino\inventory-management"
.\setup.ps1

# Or use the batch file
.\start.bat
```

### Creating an Executable

```powershell
# Install PS2EXE (one time)
Install-Module -Name ps2exe -Force

# Create executable
.\create-exe.ps1

# This creates: Start-InventorySystem.exe
```

### Manual Setup (if scripts fail)

```powershell
# Start services
docker-compose up -d

# Initialize database
docker-compose exec backend alembic upgrade head

# Create admin user
$body = @{
    username = "admin"
    email = "admin@linoprint.com"
    full_name = "מנהל מערכת"
    password = "admin123456"
    role = "admin"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/register" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"
```

## 📋 What the Setup Script Does

1. ✅ Checks if Docker Desktop is running
2. ✅ Starts PostgreSQL database
3. ✅ Starts Redis cache
4. ✅ Starts Backend API (FastAPI)
5. ✅ Starts Frontend (React) - if in Docker
6. ✅ Waits for all services to be healthy
7. ✅ Runs database migrations
8. ✅ Creates admin user (if doesn't exist)
9. ✅ Opens browser to http://localhost:5173
10. ✅ Shows login credentials

## 🎯 Distribution Package

When sharing with your business partner, include:

```
inventory-management/
├── start.bat                    ⭐ Main file to run
├── stop.bat                     Stop services
├── restart.bat                  Restart services
├── setup.ps1                    Setup script
├── QUICK_START_GUIDE.md         User guide
├── README_SETUP.md              Quick reference
├── docker-compose.yml           Docker config
├── docker-compose.dev.yml       Dev override (optional)
├── backend/                     Backend code
├── frontend/                    Frontend code
└── [other project files]
```

**Minimum Required Files:**
- `start.bat`
- `setup.ps1`
- `docker-compose.yml`
- `backend/` folder
- `frontend/` folder

## 🔍 Troubleshooting

### Script won't run

- **Issue**: PowerShell execution policy
- **Solution**: Script uses `-ExecutionPolicy Bypass` flag

### Docker not found

- **Issue**: Docker Desktop not installed/running
- **Solution**: Install Docker Desktop, wait for it to start

### Ports in use

- **Issue**: Ports 5173 or 8000 already in use
- **Solution**: Stop other applications or change ports in docker-compose.yml

### Services won't start

- **Issue**: Various Docker/network issues
- **Solution**: Check `setup.log` for details, run `docker-compose logs`

## 📞 Support

If setup fails:
1. Check `setup.log` file
2. Check Docker Desktop is running
3. Check `docker-compose logs` for errors
4. Verify ports 5173 and 8000 are available

## ✨ Next Steps After Setup

1. Login with admin credentials
2. Change admin password
3. Create inventory items
4. Add customers
5. Start receiving goods
6. Test barcode scanner (requires camera)

---

**Created**: December 2024  
**Purpose**: Simplify setup for non-technical users  
**Status**: Ready for testing



