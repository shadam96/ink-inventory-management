# Setup Instructions for Business Partner

## Quick Start (Easiest Method)

### Step 1: Install Docker Desktop

1. Download Docker Desktop from: https://www.docker.com/products/docker-desktop
2. Install and start Docker Desktop
3. Wait until Docker Desktop shows "Docker is running" (green icon)

### Step 2: Run Setup

1. **Double-click** `start.bat` file
2. Wait 2-5 minutes for setup to complete
3. Browser will open automatically

### Step 3: Login

- **URL**: http://localhost:5173
- **Username**: `admin`
- **Password**: `admin123456`

That's it! The system is running.

---

## Alternative: Create Windows Executable

If you prefer a single executable file:

1. Open PowerShell in this folder
2. Run: `.\create-exe.ps1`
3. This creates `Start-InventorySystem.exe`
4. Double-click the `.exe` file to start setup

---

## Files Included

- **`start.bat`** - Main setup script (double-click this)
- **`stop.bat`** - Stop all services
- **`restart.bat`** - Restart all services
- **`setup.ps1`** - PowerShell setup script (used by start.bat)
- **`QUICK_START_GUIDE.md`** - Detailed guide
- **`CREATE_EXECUTABLE.md`** - How to create .exe file

---

## Troubleshooting

See `QUICK_START_GUIDE.md` for detailed troubleshooting steps.

Common issues:
- Docker not running → Start Docker Desktop
- Ports in use → Stop other applications
- Services won't start → Check `setup.log` file

---

## Need Help?

Check `setup.log` for detailed error messages.



