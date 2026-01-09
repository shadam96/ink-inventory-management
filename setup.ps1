# Ink Inventory Management System - Quick Start Script
# This script automates the setup and startup of the inventory management system

param(
    [switch]$SkipDockerCheck,
    [switch]$SkipBrowser
)

$ErrorActionPreference = "Stop"
$script:ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:LogFile = Join-Path $script:ProjectRoot "setup.log"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Write-Host $logMessage
    Add-Content -Path $script:LogFile -Value $logMessage -ErrorAction SilentlyContinue
}

function Test-DockerRunning {
    Write-Log "Checking if Docker is running..."
    try {
        $dockerVersion = docker version 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Docker is not running. Please start Docker Desktop and try again." "ERROR"
            return $false
        }
        Write-Log "Docker is running ✓"
        return $true
    }
    catch {
        Write-Log "Docker is not installed or not accessible. Please install Docker Desktop." "ERROR"
        return $false
    }
}

function Start-Services {
    Write-Log "Starting Docker services..."
    Push-Location $script:ProjectRoot
    
    try {
        # Start services in detached mode
        $ErrorActionPreference = 'Continue'
        $output = docker-compose up -d 2>&1 | Out-String
        $ErrorActionPreference = 'Stop'
        
        if ($LASTEXITCODE -ne 0) {
            Write-Log "Failed to start Docker services. Check docker-compose.yml and Docker Desktop." "ERROR"
            Write-Log "Output: $output" "ERROR"
            return $false
        }
        
        Write-Log "Waiting for services to be healthy (this may take 30-60 seconds)..."
        
        # Wait for PostgreSQL
        $maxAttempts = 30
        $attempt = 0
        $postgresReady = $false
        
        while ($attempt -lt $maxAttempts -and -not $postgresReady) {
            Start-Sleep -Seconds 2
            $attempt++
            $health = docker-compose exec -T postgres pg_isready -U inventory_user -d inventory_db 2>&1
            if ($LASTEXITCODE -eq 0) {
                $postgresReady = $true
                Write-Log "PostgreSQL is ready ✓"
                break
            }
            Write-Host "." -NoNewline
        }
        Write-Host ""
        
        if (-not $postgresReady) {
            Write-Log "PostgreSQL did not become ready in time. Check logs: docker-compose logs postgres" "WARN"
        }
        
        # Wait for Redis
        $attempt = 0
        $redisReady = $false
        while ($attempt -lt 15 -and -not $redisReady) {
            Start-Sleep -Seconds 2
            $attempt++
            $health = docker-compose exec -T redis redis-cli ping 2>&1
            if ($health -match "PONG") {
                $redisReady = $true
                Write-Log "Redis is ready ✓"
                break
            }
        }
        
        # Wait for backend
        $attempt = 0
        $backendReady = $false
        while ($attempt -lt 30 -and -not $backendReady) {
            Start-Sleep -Seconds 2
            $attempt++
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 2 -ErrorAction Stop 2>&1
                if ($response.StatusCode -eq 200) {
                    $backendReady = $true
                    Write-Log "Backend API is ready ✓"
                    break
                }
            }
            catch {
                # Still starting
            }
        }
        
        if (-not $backendReady) {
            Write-Log "Backend did not become ready in time. Check logs: docker-compose logs backend" "WARN"
            Write-Log "You can still try to access the application - it may be starting up." "INFO"
        }
        
        # Wait for frontend (if running in Docker)
        $attempt = 0
        $frontendReady = $false
        while ($attempt -lt 20 -and -not $frontendReady) {
            Start-Sleep -Seconds 2
            $attempt++
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 2 -ErrorAction Stop 2>&1
                if ($response.StatusCode -eq 200) {
                    $frontendReady = $true
                    Write-Log "Frontend is ready ✓"
                    break
                }
            }
            catch {
                # Still starting or not running in Docker
            }
        }
        
        if (-not $frontendReady) {
            Write-Log "Frontend not detected in Docker. You may need to run it separately:" "INFO"
            Write-Log "  cd frontend; npm run dev" "INFO"
        }
        
        return $true
    }
    finally {
        Pop-Location
    }
}

function Initialize-Database {
    Write-Log "Initializing database (running migrations)..."
    Push-Location $script:ProjectRoot
    
    try {
        $migrationOutput = docker-compose exec -T backend alembic upgrade head 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Database migrations completed ✓"
            return $true
        }
        else {
            Write-Log "Migration failed. Output: $migrationOutput" "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Failed to run migrations: $_" "ERROR"
        return $false
    }
    finally {
        Pop-Location
    }
}

function Create-AdminUser {
    Write-Log "Creating admin user (if not exists)..."
    
    # Use ASCII-safe name to avoid encoding issues
    $adminData = @{
        username = "admin"
        email = "admin@linoprint.com"
        full_name = "System Administrator"
        password = "admin123456"
        role = "admin"
    } | ConvertTo-Json
    
    try {
        # Check if user already exists by trying to login
        $loginData = @{
            username = "admin"
            password = "admin123456"
        } | ConvertTo-Json
        
        $loginResponse = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" `
            -Method POST `
            -Body $loginData `
            -ContentType "application/json" `
            -ErrorAction SilentlyContinue
        
        if ($loginResponse) {
            Write-Log "Admin user already exists ✓"
            return $true
        }
    }
    catch {
        # User doesn't exist, try to create
    }
    
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/register" `
            -Method POST `
            -Body $adminData `
            -ContentType "application/json" `
            -TimeoutSec 10
        
        Write-Log "Admin user created successfully ✓"
        Write-Log "Username: admin" "INFO"
        Write-Log "Password: admin123456" "INFO"
        return $true
    }
    catch {
        $errorMessage = $_.Exception.Message
        if ($errorMessage -match "already exists" -or $errorMessage -match "409") {
            Write-Log "Admin user already exists ✓"
            return $true
        }
        Write-Log "Failed to create admin user: $errorMessage" "WARN"
        Write-Log "You can create it manually via the API or UI" "INFO"
        return $false
    }
}

function Open-Browser {
    if ($SkipBrowser) {
        return
    }
    
    Write-Log "Opening application in browser..."
    Start-Sleep -Seconds 2
    
    try {
        Start-Process "http://localhost:5173"
        Write-Log "Browser opened ✓"
    }
    catch {
        Write-Log "Failed to open browser automatically. Please navigate to: http://localhost:5173" "WARN"
    }
}

function Show-Status {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Setup Complete!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Application URLs:" -ForegroundColor Yellow
    Write-Host "  Frontend:  http://localhost:5173" -ForegroundColor White
    Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor White
    Write-Host ""
    Write-Host "Login Credentials:" -ForegroundColor Yellow
    Write-Host "  Username:  admin" -ForegroundColor White
    Write-Host "  Password:  admin123456" -ForegroundColor White
    Write-Host ""
    Write-Host "Useful Commands:" -ForegroundColor Yellow
    Write-Host "  View logs:     docker-compose logs -f" -ForegroundColor Gray
    Write-Host "  Stop services: docker-compose down" -ForegroundColor Gray
    Write-Host "  Restart:       docker-compose restart" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Log file: $script:LogFile" -ForegroundColor Gray
    Write-Host ""
}

# Main execution
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Ink Inventory Management System" -ForegroundColor Cyan
Write-Host "  Quick Start Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Log "Starting setup process..."

# Check Docker
if (-not $SkipDockerCheck) {
    if (-not (Test-DockerRunning)) {
        Write-Host ""
        Write-Host "ERROR: Docker is not running!" -ForegroundColor Red
        Write-Host "Please:" -ForegroundColor Yellow
        Write-Host "  1. Install Docker Desktop from https://www.docker.com/products/docker-desktop" -ForegroundColor White
        Write-Host "  2. Start Docker Desktop" -ForegroundColor White
        Write-Host "  3. Wait for Docker to be ready" -ForegroundColor White
        Write-Host "  4. Run this script again" -ForegroundColor White
        Write-Host ""
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Start services
if (-not (Start-Services)) {
    Write-Host ""
    Write-Host "ERROR: Failed to start services!" -ForegroundColor Red
    Write-Host "Check the log file: $script:LogFile" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Initialize database
Start-Sleep -Seconds 5  # Give backend a moment to fully start
if (-not (Initialize-Database)) {
    Write-Host ""
    Write-Host "WARNING: Database initialization had issues!" -ForegroundColor Yellow
    Write-Host "The application may still work. Check logs if you encounter problems." -ForegroundColor Yellow
    Write-Host ""
}

# Create admin user
Start-Sleep -Seconds 3
Create-AdminUser | Out-Null

# Open browser
Open-Browser

# Show status
Show-Status

Write-Host "Setup completed! The application should be running." -ForegroundColor Green
Write-Host ""
Read-Host "Press Enter to exit"

