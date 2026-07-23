# 📧 Email Setup Guide - Resend

Transactional email (alerts, delivery notes, test emails) is sent through
[Resend](https://resend.com). Configure it via a single environment
variable — no SMTP credentials involved.

---

## Step 1: Get a Resend API Key

1. Sign up at https://resend.com
2. Go to **API Keys** and create a new key (starts with `re_`)
3. (Optional, for production) Verify a sending domain under **Domains** so
   `EMAIL_FROM` can use your own domain instead of `onboarding@resend.dev`

## Step 2: Configure the Backend

Set these environment variables wherever the backend runs (`backend/.env`
locally, or your hosting provider's environment variable settings in
production — e.g. Render, Railway, Fly.io):

```env
RESEND_API_KEY=re_your_api_key
EMAIL_FROM=Lino Inventory <onboarding@resend.dev>
```

Restart the backend after changing environment variables — `Settings` is
read once at process startup (`app/core/config.py`).

**Production note**: the "Send Test Email" button in Settings returns
*"Email not configured. Set RESEND_API_KEY in environment variables."*
whenever this variable is missing on the server the backend is actually
running on. Setting it in a local `.env` file has no effect on a deployed
instance — it must be set in that host's environment variable panel.

---

## Testing Email Configuration

### Method 1: Using the Test Script (Easiest, local only)

```bash
cd backend
python test_email_real.py
```

This will:
1. Load your local `.env` configuration
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
4. Scroll to **Email Alerts**
5. Enter your email address next to **Send Test Email**
6. Click **Send Test**

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
  -d '{"email":"your_test_email@example.com"}'
```

---

## Troubleshooting

### Error: "Email not configured. Set RESEND_API_KEY in environment variables."

- `RESEND_API_KEY` isn't set in the environment of the backend process
  handling the request. Check the host running the backend (not just your
  local machine) and set it there.
- Restart/redeploy the backend after setting the variable — it's read once
  at startup via `app.core.config.settings`.

### Error: "Failed to send test email: ..."

- The key is set but Resend rejected the request — check the key is valid
  and not revoked, and that `EMAIL_FROM` is either `onboarding@resend.dev`
  (Resend's shared sandbox sender) or a domain you've verified in Resend.

### Emails not arriving

- Check the Resend dashboard's **Logs** tab — it shows delivery status per
  message, including bounces/spam rejections.
- Check the recipient's spam folder.

---

## Testing Automated Alerts

Once email is configured, you can test automated alert emails:

```bash
# Trigger alert check manually
curl -X POST http://localhost:8000/api/v1/alerts/run-checks \
  -H "Authorization: Bearer $TOKEN"
```

This will:
- Check for expiring batches
- Check for low stock
- Send emails to the addresses configured in Settings → Email Alerts

---

## Email Templates Available

The system includes these Hebrew RTL email templates
(`backend/app/templates/email/`):

1. **Expiration Alert** (`expiration_alert.html`)
   - Sent when batches are 30/60/90/120 days from expiration
2. **Low Stock Alert** (`low_stock_alert.html`)
   - Sent when inventory falls below reorder point
3. **Expired Batch Alert** (`expired_batch_alert.html`)
4. **Dead Stock Alert** (`dead_stock_alert.html`)
5. **Delivery Note** (`delivery_note_email.html`)
   - Sent to customers with delivery confirmations
6. **Weekly Report** (`weekly_report.html`)
7. **Test Email** (`test_email.html`)
   - Sent from the Settings page

---

## Security Best Practices

1. **Never commit `.env` files to git** ✅ (already in `.gitignore`)
2. Store `RESEND_API_KEY` as a secret in your hosting provider, not in code
3. Rotate the API key if it's ever exposed
4. Verify a sending domain in Resend for production instead of relying on
   the shared `onboarding@resend.dev` sandbox sender

---

## Verification Checklist

- [ ] `RESEND_API_KEY` set in the environment of the **running** backend (not just locally)
- [ ] `EMAIL_FROM` set to a sandbox or verified-domain sender
- [ ] Backend restarted/redeployed after setting the variable
- [ ] Test email sent successfully via Settings page
- [ ] Test email received in inbox
- [ ] Alert emails working (run checks manually)
- [ ] No errors in backend logs
