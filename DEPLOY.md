# ArcisAI Sales Agent - Deployment Guide

## Quick Deploy (One Command)

SSH into the server (139.59.28.88) and run:

```bash
cd /home/arcisai/arcisai-sales-agent && wget -O deploy-email-fix.py https://raw.githubusercontent.com/vmukti/arcisai-sales-agent/main/deploy-email-fix.py && sudo python3 deploy-email-fix.py
```

## What This Fix Does

The webhook handler currently stores leads but **never sends emails**. This patch adds:

1. **Auto-send welcome email** - When a new lead arrives via the website form, an immediate personalized email is sent
2. **Auto-schedule follow-up** - First follow-up scheduled for 24 hours later
3. **SMTP diagnostics** - New endpoint at `/api/diagnostics/smtp` to test email configuration
4. **Interaction tracking** - New endpoint at `/api/diagnostics/interactions` to see all sent emails

## After Deployment - Verify

```bash
# 1. Check SMTP is working
curl http://localhost:8000/api/diagnostics/smtp

# 2. Check existing leads
curl http://localhost:8000/api/leads

# 3. Submit a test lead on arcisai.io/contact-us

# 4. Check if email was sent
curl http://localhost:8000/api/diagnostics/interactions
```

## Environment Variables Required

Make sure these are in `/home/arcisai/arcisai-sales-agent/.env`:

```
ARCISAI_SMTP_HOST=smtp.gmail.com
ARCISAI_SMTP_PORT=587
ARCISAI_SMTP_USERNAME=marketing@adiance.com
ARCISAI_SMTP_PASSWORD=<gmail-app-password>
```

## Architecture

```
Website Form (arcisai.io/contact-us)
    -> HTTPS Proxy (arcisai-proxy.onrender.com)
    -> FastAPI Backend (139.59.28.88:8000)
    -> [NEW] Auto-email + Lead Scoring + Follow-up Scheduling
```
