# Script to create Windows executable from setup.ps1
# Requires PS2EXE module

param(
    [string]$OutputName = "Start-InventorySystem.exe"
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$inputFile = Join-Path $projectRoot "setup.ps1"
$outputFile = Join-Path $projectRoot $OutputName

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Creating Windows Executable" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if PS2EXE is installed
if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Write-Host "PS2EXE module not found. Installing..." -ForegroundColor Yellow
    try {
        Install-Module -Name ps2exe -Force -Scope CurrentUser -AllowClobber
        Write-Host "PS2EXE installed successfully!" -ForegroundColor Green
    }
    catch {
        Write-Host "Failed to install PS2EXE. Please run as Administrator or install manually:" -ForegroundColor Red
        Write-Host "  Install-Module -Name ps2exe -Force" -ForegroundColor Yellow
        exit 1
    }
}

# Import the module
Import-Module ps2exe -Force

# Check if input file exists
if (-not (Test-Path $inputFile)) {
    Write-Host "ERROR: setup.ps1 not found at: $inputFile" -ForegroundColor Red
    exit 1
}

Write-Host "Input file:  $inputFile" -ForegroundColor Gray
Write-Host "Output file: $outputFile" -ForegroundColor Gray
Write-Host ""

# Create executable
try {
    Write-Host "Creating executable..." -ForegroundColor Yellow
    
    Invoke-ps2exe -inputFile $inputFile `
        -outputFile $outputFile `
        -title "Ink Inventory Management" `
        -description "Quick Start Setup for Inventory Management System" `
        -company "LinoPrint" `
        -product "Inventory Management System" `
        -version "1.0.0.0" `
        -noConsole:$false `
        -requireAdmin:$false `
        -supportOS:([System.Environment]::OSVersion.Version.Major -ge 10)
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Executable Created Successfully!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "File location: $outputFile" -ForegroundColor Cyan
    Write-Host "File size:     $([math]::Round((Get-Item $outputFile).Length / 1KB, 2)) KB" -ForegroundColor Gray
    Write-Host ""
    Write-Host "You can now distribute this executable to users." -ForegroundColor Yellow
    Write-Host "They can double-click it to start the setup process." -ForegroundColor Yellow
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create executable" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}



