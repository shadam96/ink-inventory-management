#!/usr/bin/env python3
"""
Real Email Test Script
Sends an actual test email to verify SMTP configuration
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


async def test_real_email():
    """Test sending a real email"""
    
    print("=" * 60)
    print(">> Real Email Configuration Test")
    print("=" * 60)
    print()
    
    # Check configuration
    print("1. Checking SMTP Configuration...")
    print(f"   SMTP Host: {settings.smtp_host}")
    print(f"   SMTP Port: {settings.smtp_port}")
    print(f"   SMTP User: {settings.smtp_user}")
    print(f"   Email From: {settings.email_from}")
    print()
    
    if not settings.smtp_user or not settings.smtp_password:
        print("[X] ERROR: Email not configured!")
        print()
        print("Please update backend/.env with:")
        print("  SMTP_HOST=smtp.gmail.com")
        print("  SMTP_PORT=587")
        print("  SMTP_USER=your_email@gmail.com")
        print("  SMTP_PASSWORD=your_app_password")
        print("  EMAIL_FROM=your_email@gmail.com")
        print()
        print("See EMAIL_SETUP_GUIDE.md for detailed instructions")
        return False
    
    print("[OK] Configuration found")
    print()
    
    # Get recipient email
    print("2. Enter recipient email address:")
    recipient = input("   Email: ").strip()
    
    if not recipient or '@' not in recipient:
        print("[X] Invalid email address")
        return False
    
    print()
    print(f"3. Sending test email to {recipient}...")
    print("   (This may take a few seconds)")
    print()
    
    try:
        # Send test email
        await email_service.send_test_email(recipient)
        
        print("[OK] SUCCESS! Test email sent")
        print()
        print(f">> Check your inbox at: {recipient}")
        print()
        print("Expected email:")
        print("  - Subject: בדיקת חיבור מערכת ניהול מלאי")
        print("  - From:", settings.email_from)
        print("  - Contains: Hebrew text confirming email is working")
        print()
        print("If you don't see it:")
        print("  1. Check spam/junk folder")
        print("  2. Wait a few minutes (email may be delayed)")
        print("  3. Verify recipient email is correct")
        print()
        
        return True
        
    except Exception as e:
        print("[X] FAILED to send email")
        print()
        print("Error details:")
        print(f"  {type(e).__name__}: {str(e)}")
        print()
        print("Common issues:")
        print()
        print(">> Gmail Users:")
        print("  - Use App Password (not regular password)")
        print("  - Enable 2-Step Verification first")
        print("  - Generate at: https://myaccount.google.com/apppasswords")
        print()
        print(">> Authentication Failed:")
        print("  - Verify SMTP_USER matches EMAIL_FROM")
        print("  - Check password has no extra spaces")
        print("  - Try regenerating app password")
        print()
        print(">> Connection Issues:")
        print("  - Check firewall settings")
        print("  - Verify port 587 is not blocked")
        print("  - Try different network (mobile hotspot)")
        print()
        print("See EMAIL_SETUP_GUIDE.md for more help")
        print()
        
        return False


async def test_email_templates():
    """Test that email templates exist and can be rendered"""
    
    print("4. Testing Email Templates...")
    print()
    
    templates = [
        ("test_email.html", "Test Email"),
        ("expiration_alert.html", "Expiration Alert"),
        ("low_stock_alert.html", "Low Stock Alert"),
        ("delivery_note_email.html", "Delivery Note"),
        ("weekly_report.html", "Weekly Report"),
    ]
    
    all_ok = True
    
    for template_name, description in templates:
        try:
            # Try to render template
            if template_name == "test_email.html":
                html = email_service.render_template(template_name)
            else:
                # Skip rendering complex templates (need params)
                from jinja2 import Environment, FileSystemLoader
                from pathlib import Path
                
                template_dir = Path(__file__).parent / "app" / "templates" / "email"
                env = Environment(loader=FileSystemLoader(str(template_dir)))
                template = env.get_template(template_name)
                # Just verify it exists
                
            print(f"   [OK] {description} ({template_name})")
        except Exception as e:
            print(f"   [X] {description} ({template_name}) - {e}")
            all_ok = False
    
    print()
    
    if all_ok:
        print("[OK] All email templates found")
    else:
        print("[!] Some email templates missing")
    
    print()
    return all_ok


async def main():
    """Main test function"""
    
    # Test email sending
    email_ok = await test_real_email()
    
    if email_ok:
        # Test templates
        templates_ok = await test_email_templates()
        
        print("=" * 60)
        print(">> Test Summary")
        print("=" * 60)
        print(f"Email Sending: {'[OK] PASS' if email_ok else '[X] FAIL'}")
        print(f"Email Templates: {'[OK] PASS' if templates_ok else '[X] FAIL'}")
        print()
        
        if email_ok and templates_ok:
            print("[OK] All tests passed! Email system is working.")
            print()
            print("Next steps:")
            print("  1. Start backend: uvicorn app.main:app --reload")
            print("  2. Test from Settings page in frontend")
            print("  3. Run alert checks to test automated emails")
            print()
        else:
            print("[!] Some tests failed. See errors above.")
            print()
    else:
        print("=" * 60)
        print("[X] Email test failed - fix configuration first")
        print("=" * 60)
        print()


if __name__ == "__main__":
    print()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print()
        print("[!] Test cancelled by user")
        print()
