# 📧 Email Setup Guide - Real Email Testing

This guide will help you configure real email sending for the inventory management system.

---

## Option 1: Gmail (Recommended for Testing)

### Step 1: Enable 2-Factor Authentication

1. Go to your Google Account: https://myaccount.google.com/
2. Navigate to **Security**
3. Enable **2-Step Verification** if not already enabled

### Step 2: Generate App Password

1. Go to: https://myaccount.google.com/apppasswords
2. Select **App**: Mail
3. Select **Device**: Other (Custom name)
4. Enter name: "Inventory Management System"
5. Click **Generate**
6. **Copy the 16-character password** (format: xxxx xxxx xxxx xxxx)

### Step 3: Configure Backend

Update `backend/.env` file:

```env
# Email Configuration (Gmail)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_16_char_app_password
EMAIL_FROM=your_email@gmail.com
```

**Important**: 
- Use spaces in the app password as shown by Google, or remove them
- Don't use your regular Gmail password

---

## Option 2: Outlook/Hotmail

### Configuration

Update `backend/.env` file:

```env
# Email Configuration (Outlook)
SMTP_HOST=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USER=your_email@outlook.com
SMTP_PASSWORD=your_outlook_password
EMAIL_FROM=your_email@outlook.com
```

---

## Option 3: Custom SMTP Server

If you have your own SMTP server:

```env
# Email Configuration (Custom)
SMTP_HOST=smtp.your-domain.com
SMTP_PORT=587
SMTP_USER=your_username
SMTP_PASSWORD=your_password
EMAIL_FROM=noreply@your-domain.com
```

---

## Testing Email Configuration

### Method 1: Using the Test Script (Easiest)

I've created a test script for you. Run:

```bash
cd backend
python test_email_real.py
```

This will:
1. Load your .env configuration
2. Send a test email
3. Report success or failure

### Method 2: Using the Frontend

1. Start the backend:
```bash
cd backend
uvicorn app.main:app --reload
```

2. Start the frontend:
```bash
cd frontend
npm run dev
```

3. Navigate to: http://localhost:5173/settings
4. Scroll to **Email Settings**
5. Enter your email address
6. Click **Send** button

### Method 3: Using curl

```bash
# Get auth token first
TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"YOUR_PASSWORD"}' \
  | jq -r '.access_token')

# Send test email
curl -X POST http://localhost:8000/api/v1/settings/email/test \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"your_test_email@gmail.com"}'
```

---

## Troubleshooting

### Error: "Authentication failed"

**Gmail:**
- Make sure you're using the **App Password**, not your regular password
- Verify 2-Step Verification is enabled
- Try regenerating the App Password

**Outlook:**
- Check if "Less secure app access" is enabled (if applicable)
- Verify your password is correct

### Error: "Connection refused"

- Check SMTP_HOST and SMTP_PORT are correct
- Verify your firewall isn't blocking port 587
- Try port 465 with SSL (update code if needed)

### Error: "Email not configured"

- Make sure `backend/.env` file exists
- Verify SMTP_USER and SMTP_PASSWORD are set
- Restart the backend server after updating .env

### Error: "Timeout"

- Check your internet connection
- Some networks block SMTP ports
- Try using a different network (mobile hotspot)

---

## Testing Automated Alerts

Once email is configured, you can test automated alert emails:

### Test Expiration Alerts

```bash
# Trigger alert check manually
curl -X POST http://localhost:8000/api/v1/alerts/run-checks \
  -H "Authorization: Bearer $TOKEN"
```

This will:
- Check for expiring batches
- Check for low stock
- Send emails to admin/manager users

### Configure Alert Recipients

By default, emails are sent to users with **ADMIN** or **MANAGER** roles.

To receive alert emails:
1. Make sure your user has ADMIN or MANAGER role
2. Your user email must be set in the database
3. SMTP must be configured

---

## Email Templates Available

The system includes these Hebrew RTL email templates:

1. **Expiration Alert** (`expiration_alert.html`)
   - Sent when batches are 30/60/90/120 days from expiration
   - Includes batch details and recommendations

2. **Low Stock Alert** (`low_stock_alert.html`)
   - Sent when inventory falls below reorder point
   - Critical alerts for items below minimum stock

3. **Delivery Note** (`delivery_note_email.html`)
   - Sent to customers with delivery confirmations
   - Includes delivery note number and item count

4. **Weekly Report** (`weekly_report.html`)
   - Summary of inventory status
   - KPIs and statistics
   - Currently manual - can be scheduled

5. **Test Email** (`test_email.html`)
   - Simple test to verify configuration
   - Sent from Settings page

---

## Security Best Practices

### For Production

1. **Never commit .env file to git** ✅ (Already in .gitignore)
2. **Use environment variables** on your server
3. **Rotate passwords** regularly
4. **Use dedicated email account** for system emails
5. **Monitor email quota** to avoid limits

### Gmail Limits

- **Free Gmail**: ~500 emails/day
- **Google Workspace**: ~2,000 emails/day
- Consider using SendGrid or AWS SES for production

---

## Advanced: Using SendGrid (Production)

For production with high volume, consider SendGrid:

```bash
pip install sendgrid
```

Update email service to use SendGrid API instead of SMTP.

```env
SENDGRID_API_KEY=your_api_key
EMAIL_FROM=verified_sender@your-domain.com
```

---

## Verification Checklist

- [ ] SMTP credentials configured in `backend/.env`
- [ ] Backend server restarted after .env changes
- [ ] Test email sent successfully via Settings page
- [ ] Test email received in inbox
- [ ] Alert emails working (run checks manually)
- [ ] No errors in backend logs

---

## Next Steps

1. ✅ Configure SMTP in .env
2. ✅ Run test script: `python test_email_real.py`
3. ✅ Send test email from Settings page
4. ✅ Verify email received
5. ✅ Test automated alerts

---

**Need Help?** Check the troubleshooting section or review backend logs for error messages.
