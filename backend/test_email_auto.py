#!/usr/bin/env python3
"""
Automated Email Test — sends a test email via Resend.
No user input required.
"""
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env file explicitly
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from app.core.config import settings
from app.services.email_service import email_service


async def main():
    print()
    print("=" * 60)
    print(">> Automated Email Test (Resend)")
    print("=" * 60)
    print()

    print("Checking configuration...")
    print(f"  RESEND_API_KEY: {'***' + settings.resend_api_key[-4:] if settings.resend_api_key else '(not set)'}")
    print(f"  EMAIL_FROM: {settings.email_from}")
    print()

    if not email_service.is_configured:
        print("[X] RESEND_API_KEY not set in .env")
        print()
        print("  1. Sign up at https://resend.com")
        print("  2. Create an API key")
        print("  3. Add to backend/.env:  RESEND_API_KEY=re_...")
        return

    print("[OK] Configuration loaded")
    print()

    # Resend's test key only delivers to the account owner's email,
    # so we use a hard-coded test address here.
    recipient = "adamshacham1@gmail.com"

    print(f"Sending test email to: {recipient}")
    print()

    try:
        await email_service.send_test_email(recipient)

        print("=" * 60)
        print("[OK] SUCCESS! Test email sent!")
        print("=" * 60)
        print()
        print(f"Check inbox: {recipient}")
        print()

    except Exception as e:
        print("=" * 60)
        print("[X] FAILED to send email")
        print("=" * 60)
        print()
        print(f"  {type(e).__name__}: {e}")
        print()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Test cancelled\n")
