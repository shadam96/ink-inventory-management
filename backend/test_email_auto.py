#!/usr/bin/env python3
"""
Automated Email Test - Sends test email to SMTP_USER address
No user input required
"""
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env file explicitly
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

from app.core.config import settings
from app.services.email_service import email_service


async def main():
    """Send test email automatically"""
    
    print()
    print("=" * 60)
    print(">> Automated Email Test")
    print("=" * 60)
    print()
    
    # Check configuration
    print("Checking configuration...")
    print(f"  SMTP Host: {settings.smtp_host}")
    print(f"  SMTP Port: {settings.smtp_port}")
    print(f"  SMTP User: {settings.smtp_user}")
    print(f"  Email From: {settings.email_from}")
    print()
    
    if not settings.smtp_user or not settings.smtp_password:
        print("[X] Email not configured in .env file")
        print()
        print("Update backend/.env with your Gmail App Password")
        print("See EMAIL_SETUP_GUIDE.md for instructions")
        return
    
    print("[OK] Configuration loaded")
    print()
    
    # Send to the SMTP_USER email (send to yourself)
    recipient = settings.smtp_user
    
    print(f"Sending test email to: {recipient}")
    print("(Sending to yourself for testing)")
    print()
    
    try:
        # Send test email
        await email_service.send_test_email(recipient)
        
        print("=" * 60)
        print("[OK] SUCCESS! Test email sent!")
        print("=" * 60)
        print()
        print(f"Check your Gmail inbox: {recipient}")
        print()
        print("Expected email:")
        print("  Subject: Testing email connection")
        print("  From:", settings.email_from)
        print("  Content: Hebrew test message")
        print()
        print("If you don't see it:")
        print("  1. Check spam/junk folder")
        print("  2. Wait 1-2 minutes")
        print("  3. Check backend logs for errors")
        print()
        print("[OK] Email system is working!")
        print()
        
    except Exception as e:
        print("=" * 60)
        print("[X] FAILED to send email")
        print("=" * 60)
        print()
        print("Error:")
        print(f"  {type(e).__name__}: {str(e)}")
        print()
        
        # Specific error guidance
        error_msg = str(e).lower()
        
        if "authentication" in error_msg or "535" in error_msg:
            print(">> Authentication Failed")
            print()
            print("Solutions:")
            print("  1. Verify you're using Gmail App Password (not regular password)")
            print("  2. Generate new App Password:")
            print("     https://myaccount.google.com/apppasswords")
            print("  3. Make sure 2-Step Verification is enabled")
            print("  4. Update SMTP_PASSWORD in backend/.env")
            print()
            
        elif "connection" in error_msg or "timeout" in error_msg:
            print(">> Connection Failed")
            print()
            print("Solutions:")
            print("  1. Check internet connection")
            print("  2. Verify firewall allows port 587")
            print("  3. Try different network (mobile hotspot)")
            print()
            
        else:
            print(">> Unknown Error")
            print()
            print("Check:")
            print("  1. SMTP_USER and SMTP_PASSWORD in .env")
            print("  2. No typos in email address")
            print("  3. App Password has no extra spaces")
            print()
        
        print("See EMAIL_SETUP_GUIDE.md for detailed troubleshooting")
        print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("[!] Test cancelled")
        print()
