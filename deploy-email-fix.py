#!/usr/bin/env python3
"""
ArcisAI Sales Agent - Auto-Email Fix Deployment Script
Run on server: python3 deploy-email-fix.py

This script patches the existing webhook_handler.py to:
1. Auto-send welcome email when new lead arrives
2. Auto-schedule follow-up for 24 hours later
3. Add SMTP diagnostic endpoint
"""

import os
import re
import shutil
import subprocess
import sys
from datetime import datetime

# Configuration
DEPLOY_PATHS = [
    "/home/arcisai/arcisai-sales-agent",
    "/opt/arcisai-sales-agent",
]
SERVICE_NAME = "arcisai-sales-agent"

def find_deploy_path():
    for path in DEPLOY_PATHS:
        if os.path.exists(os.path.join(path, "integrations", "webhook_handler.py")):
            return path
    print("ERROR: Could not find arcisai-sales-agent installation")
    sys.exit(1)

def backup_file(filepath):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{filepath}.backup_{ts}"
    shutil.copy2(filepath, backup)
    print(f"Backup: {backup}")
    return backup

def patch_webhook_handler(deploy_path):
    wh_path = os.path.join(deploy_path, "integrations", "webhook_handler.py")
    print(f"\nPatching: {wh_path}")

    backup_file(wh_path)

    with open(wh_path, 'r') as f:
        content = f.read()

    # ================================================================
    # PATCH 1: Add 'import asyncio' and 'import traceback' if missing
    # ================================================================
    if 'import asyncio' not in content:
        content = 'import asyncio\n' + content
        print("  + Added: import asyncio")
    if 'import traceback' not in content:
        content = content.replace('import asyncio\n', 'import asyncio\nimport traceback\n', 1)
        print("  + Added: import traceback")
    if 'from datetime import datetime, timedelta' not in content:
        content = content.replace(
            'from datetime import datetime',
            'from datetime import datetime, timedelta'
        )
        print("  + Added: timedelta import")

    # ================================================================
    # PATCH 2: Add auto-followup scheduling in create_lead
    # ================================================================
    # Find create_lead method and add next_followup_at scheduling
    if 'next_followup_at' not in content or 'timedelta(hours=24)' not in content:
        # Find where lead is stored in create_lead
        old_store = 'self.leads[lead_data.id] = lead_data'
        new_store = '''# AUTO FOLLOW-UP SCHEDULING - Schedule first follow-up for 24 hours
            lead_data.next_followup_at = datetime.utcnow() + timedelta(hours=24)

            self.leads[lead_data.id] = lead_data'''
        if old_store in content:
            content = content.replace(old_store, new_store, 1)
            print("  + Added: Auto follow-up scheduling (24h)")

    # ================================================================
    # PATCH 3: Add _send_welcome_email method
    # ================================================================
    WELCOME_EMAIL_METHOD = '''
    async def _send_welcome_email(self, lead) -> bool:
        """
        CRITICAL FIX: Auto-send personalized welcome email to new leads.
        This was the missing piece - leads were stored but never contacted.
        """
        if not lead.email or not self.email_sender:
            logger.warning(f"Cannot send welcome email: email={'yes' if lead.email else 'no'}, sender={'yes' if self.email_sender else 'no'}")
            return False

        try:
            name = lead.name or "there"
            first_name = name.split()[0] if name != "there" else "there"
            company = lead.company or "your organization"
            metadata = lead.metadata or {}
            cameras_for = metadata.get("cameras_for", "your facility")
            quantity = metadata.get("quantity", "")

            # Score-based email tone
            if lead.score >= 75:
                urgency = "I'm personally reaching out because your requirements are a great fit for our solutions."
            elif lead.score >= 50:
                urgency = "Based on your requirements, I believe we have some excellent solutions for you."
            else:
                urgency = "Thank you for reaching out - we'd love to learn more about your needs."

            # Build subject
            if company and company != "your organization":
                subject = f"{company} x ArcisAI - AI CCTV Solutions Tailored for You"
            else:
                subject = f"Hi {first_name}, Your ArcisAI Security Consultation"

            # Build HTML email
            html_body = f"""
            <html>
            <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
                <div style="max-width: 640px; margin: 0 auto; background: #ffffff;">
                    <div style="background: linear-gradient(135deg, #1e3a8a, #3b82f6); padding: 30px; text-align: center;">
                        <h1 style="color: white; margin: 0; font-size: 28px;">ArcisAI</h1>
                        <p style="color: #93c5fd; margin: 8px 0 0 0; font-size: 14px;">India's AI-First CCTV Security Platform</p>
                    </div>
                    <div style="padding: 30px;">
                        <p style="font-size: 16px;">Hi {first_name},</p>
                        <p>{urgency}</p>
                        <p>I noticed you're looking for <strong>{cameras_for}</strong> security solutions{' for ' + company if company != 'your organization' else ''}{' (' + quantity + ' cameras)' if quantity else ''}. That's exactly what we specialize in.</p>
                        <div style="background: #f0f9ff; border-left: 4px solid #1e3a8a; padding: 20px; margin: 20px 0; border-radius: 0 8px 8px 0;">
                            <h3 style="margin-top: 0; color: #1e3a8a;">Why ArcisAI?</h3>
                            <p><strong>100% Made in India</strong> - Non-Chinese SoC, STQC certified for government</p>
                            <p><strong>AI-Powered Analytics</strong> - 8+ edge AI detections in under 500ms</p>
                            <p><strong>ArcisGPT</strong> - India's first Gen AI for CCTV video search</p>
                            <p><strong>70% bandwidth savings</strong> - Intelligent compression + edge processing</p>
                        </div>
                        <p>To help me recommend the perfect solution, could you share:</p>
                        <ol>
                            <li>What's your <strong>budget range</strong> for the project?</li>
                            <li>What's your <strong>timeline</strong> - when do you need cameras installed?</li>
                            <li>Do you have any <strong>existing CCTV infrastructure</strong> we'd need to integrate with?</li>
                        </ol>
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="https://arcisai.io/products" style="background: #1e3a8a; color: white; padding: 14px 36px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold; font-size: 16px;">
                                Explore Our Products
                            </a>
                        </div>
                        <p style="color: #666; font-size: 14px;">Or just reply to this email - I'll personally get back to you within a few hours.</p>
                        <div style="border-top: 1px solid #eee; padding-top: 20px; margin-top: 20px;">
                            <p style="margin: 0;"><strong>ArcisAI Sales Team</strong></p>
                            <p style="margin: 4px 0; color: #666; font-size: 14px;">
                                Website: <a href="https://arcisai.io">arcisai.io</a> |
                                WhatsApp: <a href="https://wa.me/918320551897">+91 83205 51897</a>
                            </p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """

            # Send the email
            result = self.email_sender.send_email(
                to_email=lead.email,
                subject=subject,
                body=html_body,
                html=True
            )

            if result:
                lead.status = "contacted"
                lead.last_contacted_at = datetime.utcnow()
                self.leads[lead.id] = lead  # Update in storage

                # Track interaction
                self.interactions.append({
                    "lead_id": lead.id,
                    "type": "email_sent",
                    "channel": "email",
                    "subject": subject,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "sent"
                })
                logger.info(f"Welcome email SENT to {lead.email} (lead: {lead.id}, score: {lead.score})")
            else:
                logger.error(f"Welcome email FAILED for {lead.email}")
                self.interactions.append({
                    "lead_id": lead.id,
                    "type": "email_failed",
                    "channel": "email",
                    "subject": subject,
                    "timestamp": datetime.utcnow().isoformat(),
                    "status": "failed"
                })

            return bool(result)

        except Exception as e:
            logger.error(f"Welcome email error for {lead.email}: {e}\\n{traceback.format_exc()}")
            return False
'''

    if '_send_welcome_email' not in content:
        # Insert before handle_webhook_lead or after create_lead
        # Find the handle_webhook_lead method
        insert_markers = [
            'async def handle_webhook_lead',
            'def handle_webhook_lead',
            '# Webhook endpoints',
            '# =====\n    # API Routes',
        ]
        inserted = False
        for marker in insert_markers:
            if marker in content:
                content = content.replace(marker, WELCOME_EMAIL_METHOD + '\n    ' + marker, 1)
                inserted = True
                print("  + Added: _send_welcome_email method")
                break

        if not inserted:
            # Fallback: insert after create_lead method
            # Find end of create_lead by looking for next method definition
            create_lead_pos = content.find('async def create_lead')
            if create_lead_pos > 0:
                # Find next method after create_lead
                next_method = content.find('\n    async def ', create_lead_pos + 10)
                if next_method < 0:
                    next_method = content.find('\n    def ', create_lead_pos + 10)
                if next_method > 0:
                    content = content[:next_method] + '\n' + WELCOME_EMAIL_METHOD + content[next_method:]
                    inserted = True
                    print("  + Added: _send_welcome_email method (fallback insertion)")

        if not inserted:
            print("  ! WARNING: Could not insert _send_welcome_email - manual edit needed")
    else:
        print("  = _send_welcome_email already exists")

    # ================================================================
    # PATCH 4: Call _send_welcome_email in handle_webhook_lead
    # ================================================================
    AUTO_EMAIL_CALL = '''
            # ===== AUTO-EMAIL: Send welcome email to new lead =====
            try:
                import asyncio
                asyncio.create_task(self._send_welcome_email(lead))
                logger.info(f"Auto-email task created for lead {lead.id}")
            except Exception as email_err:
                logger.error(f"Auto-email task creation failed: {email_err}")
'''

    if 'create_task(self._send_welcome_email' not in content:
        # Find where lead is returned in handle_webhook_lead
        # Common patterns in the existing code
        webhook_patterns = [
            ('return {"lead_id": lead.id', AUTO_EMAIL_CALL + '\n            return {"lead_id": lead.id'),
            ('return {"lead_id": lead_id', AUTO_EMAIL_CALL + '\n            return {"lead_id": lead_id'),
            ('"status": "created"', '"status": "contacted"'),  # Also update status
        ]

        patched_auto_email = False
        for old, new in webhook_patterns[:2]:
            if old in content:
                content = content.replace(old, new, 1)
                patched_auto_email = True
                print("  + Added: Auto-email call in handle_webhook_lead")
                break

        if not patched_auto_email:
            print("  ! WARNING: Could not add auto-email call - check handle_webhook_lead manually")
    else:
        print("  = Auto-email call already exists")

    # ================================================================
    # PATCH 5: Add SMTP diagnostic endpoint to create_app
    # ================================================================
    SMTP_DIAGNOSTIC = '''
    @app.get("/api/diagnostics/smtp")
    async def smtp_diagnostic():
        """Test SMTP connection and report status."""
        import smtplib
        results = {"smtp_configured": False, "connection": "not_tested", "auth": "not_tested"}

        smtp_host = os.environ.get("ARCISAI_SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("ARCISAI_SMTP_PORT", "587"))
        smtp_user = os.environ.get("ARCISAI_SMTP_USERNAME", "")
        smtp_pass = os.environ.get("ARCISAI_SMTP_PASSWORD", "")

        results["smtp_host"] = smtp_host
        results["smtp_port"] = smtp_port
        results["smtp_username"] = smtp_user[:3] + "***" if smtp_user else "NOT SET"
        results["smtp_password"] = "SET" if smtp_pass else "NOT SET"
        results["smtp_configured"] = bool(smtp_user and smtp_pass)

        if smtp_user and smtp_pass:
            try:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
                server.starttls()
                results["connection"] = "success"
                try:
                    server.login(smtp_user, smtp_pass)
                    results["auth"] = "success"
                except Exception as auth_err:
                    results["auth"] = f"failed: {str(auth_err)}"
                server.quit()
            except Exception as conn_err:
                results["connection"] = f"failed: {str(conn_err)}"

        results["email_sender_loaded"] = handler.email_sender is not None if 'handler' in dir() else "unknown"
        return results

    @app.get("/api/diagnostics/interactions")
    async def get_interactions():
        """Get all tracked email interactions."""
        return {"interactions": handler.interactions, "total": len(handler.interactions)}
'''

    if '/api/diagnostics/smtp' not in content:
        # Find the end of create_app function, before 'return app'
        return_app_pos = content.rfind('return app')
        if return_app_pos > 0:
            content = content[:return_app_pos] + SMTP_DIAGNOSTIC + '\n    ' + content[return_app_pos:]
            print("  + Added: SMTP diagnostic endpoint")
            print("  + Added: Interactions tracking endpoint")
        else:
            print("  ! WARNING: Could not add diagnostic endpoints")
    else:
        print("  = Diagnostic endpoints already exist")

    # ================================================================
    # PATCH 6: Fix follow-up to use default template
    # ================================================================
    if "template = template or 'followup'" not in content and 'trigger_followup' in content:
        old_trigger = 'async def trigger_followup'
        if old_trigger in content:
            # Add default template logic after the function signature
            content = content.replace(
                'if not template and not custom_message:',
                'if not template and not custom_message:\n                template = "followup"  # Use default follow-up template',
                1
            )
            print("  + Added: Default follow-up template")

    # Write patched file
    with open(wh_path, 'w') as f:
        f.write(content)

    print(f"\nPatched file written: {wh_path}")
    return True

def restart_service():
    print(f"\nRestarting service: {SERVICE_NAME}")
    try:
        subprocess.run(["systemctl", "restart", SERVICE_NAME], check=True)
        import time
        time.sleep(3)
        result = subprocess.run(
            ["systemctl", "is-active", SERVICE_NAME],
            capture_output=True, text=True
        )
        status = result.stdout.strip()
        if status == "active":
            print(f"Service status: ACTIVE (running)")
            return True
        else:
            print(f"Service status: {status}")
            print("Check logs: journalctl -u arcisai-sales-agent -n 50")
            return False
    except Exception as e:
        print(f"Service restart error: {e}")
        return False

def test_smtp():
    """Quick SMTP test."""
    print("\nTesting SMTP connection...")
    try:
        import smtplib
        from dotenv import load_dotenv

        # Try loading .env
        for path in DEPLOY_PATHS:
            env_file = os.path.join(path, ".env")
            if os.path.exists(env_file):
                load_dotenv(env_file)
                break

        host = os.environ.get("ARCISAI_SMTP_HOST", "smtp.gmail.com")
        port = int(os.environ.get("ARCISAI_SMTP_PORT", "587"))
        user = os.environ.get("ARCISAI_SMTP_USERNAME", "")
        pwd = os.environ.get("ARCISAI_SMTP_PASSWORD", "")

        print(f"  SMTP: {host}:{port}")
        print(f"  User: {user[:5]}***" if user else "  User: NOT SET")
        print(f"  Pass: {'SET' if pwd else 'NOT SET'}")

        if user and pwd:
            server = smtplib.SMTP(host, port, timeout=10)
            server.starttls()
            server.login(user, pwd)
            server.quit()
            print("  SMTP connection: SUCCESS")
            return True
        else:
            print("  SMTP: Missing credentials")
            return False
    except Exception as e:
        print(f"  SMTP test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("ArcisAI Sales Agent - Auto-Email Fix")
    print("=" * 60)

    deploy_path = find_deploy_path()
    print(f"Deploy path: {deploy_path}")

    # Apply patches
    success = patch_webhook_handler(deploy_path)

    if success:
        # Test SMTP
        test_smtp()

        # Restart service
        restart_service()

        print("\n" + "=" * 60)
        print("DEPLOYMENT COMPLETE!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Test SMTP: curl http://localhost:8000/api/diagnostics/smtp")
        print("2. Check leads: curl http://localhost:8000/api/leads")
        print("3. Submit test lead on arcisai.io/contact-us")
        print("4. Verify email was sent: curl http://localhost:8000/api/diagnostics/interactions")
    else:
        print("\nDEPLOYMENT FAILED - check errors above")
