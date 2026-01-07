# Creating a Windows Executable

If you want to convert the setup script into a standalone `.exe` file, you have several options:

## Option 1: Use PS2EXE (Recommended)

PS2EXE converts PowerShell scripts to Windows executables.

### Installation:

1. Open PowerShell as Administrator
2. Run:
```powershell
Install-Module -Name ps2exe -Force
```

### Create Executable:

```powershell
cd "C:\Users\Adam Shacham\Lino\inventory-management"
Invoke-ps2exe -inputFile "setup.ps1" -outputFile "Start-InventorySystem.exe" -iconFile "icon.ico" -title "Ink Inventory Management" -description "Quick Start Setup" -company "LinoPrint" -product "Inventory Management" -version "1.0.0.0"
```

## Option 2: Use Bat To Exe Converter

1. Download Bat To Exe Converter: https://www.battoexeconverter.com/
2. Open the tool
3. Load `start.bat`
4. Set options:
   - **Invisible**: Unchecked (so user sees progress)
   - **Include batch file**: Checked
   - **Run as administrator**: Unchecked (unless needed)
5. Click "Compile" and save as `Start-InventorySystem.exe`

## Option 3: Use IExpress (Built into Windows)

1. Open Command Prompt
2. Run: `iexpress`
3. Follow the wizard:
   - Select "Create new Self Extraction Directive file"
   - Extract files to temporary folder
   - Add `start.bat` as the installation program
   - Set extraction path to current directory
   - Create the executable

## Option 4: Use WinRAR / 7-Zip SFX

1. Create a ZIP with `start.bat` and `setup.ps1`
2. Use WinRAR or 7-Zip to create a self-extracting archive
3. Set `start.bat` as the file to run after extraction

## Recommended Approach

For your business partner, **Option 1 (PS2EXE)** is best because:
- ✅ Creates a true executable
- ✅ Can include icon and version info
- ✅ Single file distribution
- ✅ No extraction needed

## Quick Setup Script for PS2EXE

Save this as `create-exe.ps1`:

```powershell
# Install PS2EXE if not already installed
if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Write-Host "Installing PS2EXE module..."
    Install-Module -Name ps2exe -Force -Scope CurrentUser
}

# Create executable
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$inputFile = Join-Path $projectRoot "setup.ps1"
$outputFile = Join-Path $projectRoot "Start-InventorySystem.exe"

Write-Host "Creating executable: $outputFile"
Invoke-ps2exe -inputFile $inputFile `
    -outputFile $outputFile `
    -title "Ink Inventory Management" `
    -description "Quick Start Setup for Inventory Management System" `
    -company "LinoPrint" `
    -product "Inventory Management" `
    -version "1.0.0.0" `
    -noConsole:$false `
    -requireAdmin:$false

Write-Host "Executable created successfully!"
Write-Host "File location: $outputFile"
```

Run it:
```powershell
.\create-exe.ps1
```

## Distribution

After creating the executable:

1. **Test it** on a clean Windows machine (or VM)
2. **Package it** with:
   - `docker-compose.yml`
   - `backend/` folder
   - `frontend/` folder
   - `Start-InventorySystem.exe`
   - `QUICK_START_GUIDE.md`
3. **Create a ZIP** with all files
4. **Share** with your business partner

## Alternative: Simple Batch File (Current Solution)

The current `start.bat` file works perfectly fine and doesn't require any additional tools. Your business partner can simply:
- Double-click `start.bat`
- Follow the on-screen instructions

This is actually simpler than an executable for non-technical users because:
- ✅ No installation needed
- ✅ Easy to update (just edit the .bat file)
- ✅ Works on all Windows versions
- ✅ Can see what's happening

## Recommendation

**Use the batch file approach (`start.bat`)** - it's simpler and more maintainable. Only create an executable if:
- You need to hide the code
- You want a custom icon
- You're distributing to many users
- You need version information

For a single business partner, the batch file is perfect!



