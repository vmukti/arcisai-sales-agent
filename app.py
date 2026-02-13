"""
ArcisAI Independent AI Sales Agent - Web App
Deploy on Render.com: python app.py
Your team uploads leads -> AI sends personalized emails + WhatsApp automatically
"""
import os, json, smtplib, uuid, socket, urllib.request, urllib.error, base64, urllib.parse
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Config - Email provider: "resend" (HTTP API, works on Render) or "smtp"
EMAIL_PROVIDER = os.environ.get("EMAIL_PROVIDER", "resend")
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "marketing@adiance.com")
SMTP_PASS = os.environ.get("SMTP_PASS", "wtzvxbtxgolkblue")
FROM_NAME = "ArcisAI Sales Team"
LEADS_FILE = "leads_db.json"

# Config - WhatsApp via Twilio
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "+14155238886")
BUSINESS_WHATSAPP = "+919687779999"

def load_leads():
    if os.path.exists(LEADS_FILE):
        with open(LEADS_FILE) as f:
            return json.load(f)
    return []

def save_leads(leads):
    with open(LEADS_FILE, "w") as f:
        json.dump(leads, f, indent=2, default=str)

def score_lead(name, company, requirement, customer_type=""):
    score = 30
    req = (requirement or "").lower()
    ct = (customer_type or "").lower()
    if any(w in req for w in ["government", "smart city", "defense", "military"]) or "government" in ct: score += 30
    if any(w in req for w in ["factory", "warehouse", "hospital", "school", "bank", "enterprise"]) or "enterprise" in ct: score += 20
    if any(w in req for w in ["100", "200", "500", "bulk", "large", "project"]): score += 15
    if any(w in req for w in ["50", "cctv", "camera", "surveillance", "security"]): score += 10
    if company and company.lower() not in ["na", "none", "", "n/a"]: score += 10
    if any(w in req for w in ["urgent", "immediate", "asap", "this month"]): score += 5
    if "si" in ct or "dealer" in ct: score += 10
    return min(score, 100)

def build_email_html(first_name, company, requirement, score, customer_type=""):
    """Build personalized email based on customer type - short, personal, action-oriented"""
    ct = (customer_type or "").lower()
    wa_link = "https://wa.me/919687779999"
    req_display = requirement or "security cameras"
    priority = "HIGH PRIORITY" if score >= 75 else "MEDIUM" if score >= 50 else "NORMAL"

    # Subject line - feels personal, not automated
    if company and company.lower() not in ["na", "none", "", "n/a"]:
        subject = f"Re: {company} \u2014 camera requirement"
    else:
        subject = f"Re: Your camera inquiry, {first_name}"

    co = f" for {company}" if company and company.lower() not in ["na", "none", "", "n/a"] else ""

    # Customer-type-specific paragraphs
    if ct == "si":
        p1 = f"Just saw your inquiry \u2014 {req_display}{co}. We can definitely help with this."
        p2 = "We work with 200+ SI partners across India and offer competitive project margins. Our S-Series has 8 edge AI features including PPE, Fire, LPR, and Crowd Analysis \u2014 all STQC certified, non-Chinese SoC."
        p3 = "Happy to share the SI price list and discuss your project scope. When would be a good time for a quick call?"
    elif ct == "dealer":
        p1 = f"Thanks for your interest in ArcisAI \u2014 {req_display}{co}."
        p2 = "We're actively expanding our dealer network and offer strong margins on both S-Series (premium) and Eco-Series (budget-friendly at ~$50/camera). Full marketing and technical support included."
        p3 = "Want to see the dealer price list and MOQ details? Let's connect."
    elif ct == "government":
        p1 = f"Thank you for your inquiry regarding {req_display}{co}."
        p2 = "ArcisAI is STQC certified and listed on GeM \u2014 fully compliant for government procurement. Our cameras use non-Chinese SoC (Made in India), with BIS, ISO 27001, and all required certifications."
        p3 = "I can share the STQC certificate, GeM listing details, and a detailed technical spec sheet. Shall I send those over?"
    elif ct == "enterprise":
        p1 = f"Just saw your requirement \u2014 {req_display}{co}. This is right in our wheelhouse."
        p2 = "We've deployed across 500+ enterprise sites in India. Our edge AI processes everything locally (no cloud dependency, <500ms latency) with 8 detection types including intrusion, fire, PPE, and crowd analytics."
        p3 = "I'd love to set up a 15-min live demo tailored to your use case. What day works?"
    elif ct == "residential":
        p1 = f"Thanks for reaching out about {req_display}{co}!"
        p2 = "Our Eco-Series is perfect for homes and small businesses \u2014 affordable AI cameras starting at ~$50 with smart alerts, night vision, and easy mobile app access. Plug-and-play setup."
        p3 = "Want me to recommend the right package for your space? Just tell me how many cameras you're thinking."
    else:
        p1 = f"Thanks for your interest in ArcisAI \u2014 {req_display}{co}."
        p2 = "We offer India's most advanced AI CCTV platform with edge processing, 8 detection types, and full STQC certification. From 4-camera setups to 1000+ camera deployments, we've got you covered."
        p3 = "I'd love to understand your needs better. Would a quick call work, or shall I send over a product comparison?"

    html = f"""<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0;">
<div style="max-width: 600px; margin: 0 auto; padding: 20px;">
    <p style="font-size: 15px;">Hi {first_name},</p>
    <p style="font-size: 15px;">{p1}</p>
    <p style="font-size: 15px;">{p2}</p>
    <p style="font-size: 15px;">{p3}</p>
    <div style="margin: 25px 0;">
        <a href="{wa_link}" style="background: #25D366; color: white; padding: 12px 28px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 600; font-size: 14px;">WhatsApp Us</a>
        <span style="color: #888; font-size: 13px; margin-left: 10px;">or call +91 96877 79999</span>
    </div>
    <p style="margin: 0; font-size: 14px;">Regards,</p>
    <p style="margin: 4px 0; font-size: 14px;"><strong>ArcisAI Sales Team</strong></p>
    <p style="margin: 2px 0; color: #888; font-size: 13px;">arcisai.io | marketing@arcisai.io</p>
</div>
</body>
</html>"""
    return subject, html, priority

# ============ WHATSAPP MESSAGE BUILDER ============
def build_whatsapp_message(first_name, company, requirement, customer_type=""):
    """Build a short, conversational WhatsApp message based on customer type"""
    ct = (customer_type or "").lower()
    req_short = (requirement or "security cameras")[:80]
    co = f" ({company})" if company and company.lower() not in ["na", "none", "", "n/a"] else ""

    if ct == "si":
        msg = f"""Hi {first_name}{co}! \U0001f44b

Got your inquiry for {req_short}. We work with 200+ SI partners across India.

Quick highlights:
\u2713 S-Series: 8 Edge AI features (STQC certified)
\u2713 Eco-Series: ~$50/camera for cost-sensitive projects
\u2713 Competitive SI margins & project support

Happy to share the SI price list. When can we do a quick call?

\u2014 ArcisAI Sales Team
arcisai.io"""
    elif ct == "dealer":
        msg = f"""Hi {first_name}{co}! \U0001f44b

Thanks for your interest in becoming an ArcisAI partner!

We offer:
\u2713 Strong dealer margins on S-Series & Eco-Series
\u2713 Marketing & technical support
\u2713 Training & certification programs
\u2713 STQC certified, Made in India products

Want to see the dealer price list? Let's connect!

\u2014 ArcisAI Sales Team
arcisai.io"""
    elif ct == "government":
        msg = f"""Hi {first_name}{co}! \U0001f44b

Thank you for your inquiry regarding {req_short}.

ArcisAI is:
\u2713 STQC Certified & GeM Listed
\u2713 Non-Chinese SoC (Made in India)
\u2713 BIS, ISO 27001, CE, FCC certified
\u2713 8 Edge AI detection features

Can share STQC certificate & technical specs. Shall I send those?

\u2014 ArcisAI Sales Team
arcisai.io"""
    elif ct == "enterprise":
        msg = f"""Hi {first_name}{co}! \U0001f44b

Just saw your requirement for {req_short}. This is right in our wheelhouse!

ArcisAI offers:
\u2713 Edge AI processing (<500ms latency)
\u2713 8 detection types (intrusion, fire, PPE, LPR)
\u2713 Deployed at 500+ enterprise sites
\u2713 Scalable from 10 to 1000+ cameras

Want a 15-min live demo? Let me know what day works!

\u2014 ArcisAI Sales Team
arcisai.io"""
    elif ct == "residential":
        msg = f"""Hi {first_name}{co}! \U0001f44b

Thanks for reaching out about {req_short}!

Our Eco-Series is perfect for homes:
\u2713 AI cameras starting at ~$50
\u2713 Smart alerts & night vision
\u2713 Easy mobile app access
\u2713 Plug-and-play setup

How many cameras are you thinking? I'll recommend the right package!

\u2014 ArcisAI Sales Team
arcisai.io"""
    else:
        msg = f"""Hi {first_name}{co}! \U0001f44b

Thanks for your interest in ArcisAI! Got your inquiry about {req_short}.

We offer India's most advanced AI CCTV:
\u2713 8 Edge AI detection features
\u2713 S-Series (premium) & Eco-Series (affordable)
\u2713 STQC certified, Made in India
\u2713 4-camera to 1000+ camera deployments

Would love to understand your needs better. Quick call or should I send a product comparison?

\u2014 ArcisAI Sales Team
arcisai.io"""

    return msg

# ============ WHATSAPP SENDER (Twilio REST API) ============
def format_phone_for_whatsapp(phone):
    """Format phone number for WhatsApp (E.164 format)"""
    if not phone:
        return None
    # Remove spaces, dashes, dots, parentheses
    cleaned = phone.strip().replace(" ", "").replace("-", "").replace(".", "").replace("(", "").replace(")", "")
    # Remove leading + if present (we'll add it back)
    if cleaned.startswith("+"):
        cleaned = cleaned[1:]
    # If starts with 91 and is 12 digits, it's Indian
    if cleaned.startswith("91") and len(cleaned) == 12:
        return f"+{cleaned}"
    # If 10 digits, assume Indian number
    if len(cleaned) == 10 and cleaned[0] in "6789":
        return f"+91{cleaned}"
    # If already has country code (11+ digits)
    if len(cleaned) >= 11:
        return f"+{cleaned}"
    return None

def send_whatsapp_twilio(to_phone, message_body):
    """Send WhatsApp message via Twilio REST API using urllib (no external library needed)"""
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        raise Exception("Twilio credentials not configured")

    formatted_phone = format_phone_for_whatsapp(to_phone)
    if not formatted_phone:
        raise Exception(f"Invalid phone number: {to_phone}")

    # Twilio Messages API endpoint
    url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"

    # Basic auth: base64(SID:AuthToken)
    auth_str = base64.b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()).decode()

    # Form-encoded body (Twilio uses application/x-www-form-urlencoded)
    payload = urllib.parse.urlencode({
        "From": f"whatsapp:{TWILIO_WHATSAPP_FROM}",
        "To": f"whatsapp:{formatted_phone}",
        "Body": message_body
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Basic {auth_str}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "ArcisAI-SalesAgent/1.0"
        },
        method="POST"
    )

    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read().decode())
        sid = result.get("sid", "")
        status = result.get("status", "")
        return True, f"sent (sid: {sid}, status: {status})"
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise Exception(f"Twilio API error {e.code}: {body}")

# ============ EMAIL SENDERS ============
def send_email_resend(to_email, subject, html_body):
    """Send email via Resend HTTP API (works on Render free tier)"""
    if not RESEND_API_KEY:
        raise Exception("RESEND_API_KEY not configured")
    payload = json.dumps({
        "from": f"{FROM_NAME} <onboarding@resend.dev>",
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "reply_to": SMTP_USER
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "ArcisAI-SalesAgent/1.0"
        },
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode())
        return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise Exception(f"Resend API error {e.code}: {body}")

def send_email_smtp(to_email, subject, html_body):
    """Send email via SMTP (for servers that allow outbound SMTP)"""
    msg = MIMEMultipart("alternative")
    msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg["Reply-To"] = SMTP_USER
    msg.attach(MIMEText(html_body, "html"))
    errors = []
    for method in ["ssl", "tls"]:
        try:
            if method == "ssl":
                server = smtplib.SMTP_SSL(SMTP_HOST, 465, timeout=8)
            else:
                server = smtplib.SMTP(SMTP_HOST, 587, timeout=8)
                server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
            server.quit()
            return True
        except Exception as e:
            errors.append(f"{method}: {str(e)}")
    raise Exception(" | ".join(errors))

def send_email(to_email, subject, html_body):
    """Route to correct email provider"""
    if EMAIL_PROVIDER == "resend" and RESEND_API_KEY:
        return send_email_resend(to_email, subject, html_body)
    elif EMAIL_PROVIDER == "smtp":
        return send_email_smtp(to_email, subject, html_body)
    else:
        raise Exception("No email provider configured. Set RESEND_API_KEY or EMAIL_PROVIDER=smtp")

# ============ HTML TEMPLATE ============
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ArcisAI Sales Agent</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#f0f4f8;color:#333}
.header{background:linear-gradient(135deg,#1e3a8a,#3b82f6);color:white;padding:20px 30px;display:flex;justify-content:space-between;align-items:center}
.header h1{font-size:24px}.header span{font-size:14px;opacity:0.8}
.container{max-width:1200px;margin:20px auto;padding:0 20px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:15px;margin-bottom:25px}
.stat-card{background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.08)}
.stat-card h3{font-size:14px;color:#666;margin-bottom:5px}.stat-card .num{font-size:32px;font-weight:700;color:#1e3a8a}
.stat-card .num.green{color:#16a34a}
.card{background:white;border-radius:12px;padding:25px;box-shadow:0 2px 8px rgba(0,0,0,0.08);margin-bottom:20px}
.card h2{color:#1e3a8a;margin-bottom:15px;font-size:20px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}
label{display:block;font-size:14px;font-weight:600;color:#555;margin-bottom:5px}
input,select,textarea{width:100%;padding:10px 14px;border:2px solid #e2e8f0;border-radius:8px;font-size:14px;transition:border 0.2s}
input:focus,select:focus,textarea:focus{outline:none;border-color:#3b82f6}
textarea{grid-column:1/-1;height:80px;resize:vertical}
.btn{background:#1e3a8a;color:white;border:none;padding:12px 30px;border-radius:8px;font-size:16px;font-weight:600;cursor:pointer;transition:background 0.2s}
.btn:hover{background:#1e40af}.btn:disabled{background:#94a3b8;cursor:not-allowed}
.btn-row{grid-column:1/-1;text-align:right;margin-top:5px}
.leads-table{width:100%;border-collapse:collapse;margin-top:10px}
.leads-table th{background:#f8fafc;padding:12px;text-align:left;font-size:13px;color:#666;border-bottom:2px solid #e2e8f0}
.leads-table td{padding:12px;border-bottom:1px solid #f1f5f9;font-size:14px}
.badge{display:inline-block;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:600}
.badge-sent{background:#dcfce7;color:#166534}.badge-failed{background:#fef2f2;color:#991b1b}
.badge-pending{background:#fef9c3;color:#854d0e}.badge-skipped{background:#f1f5f9;color:#64748b}
.badge-high{background:#fee2e2;color:#991b1b}.badge-medium{background:#fef9c3;color:#854d0e}.badge-normal{background:#e0f2fe;color:#075985}
.score{font-weight:700;font-size:16px}
.score-high{color:#dc2626}.score-med{color:#d97706}.score-low{color:#2563eb}
.msg{padding:12px 16px;border-radius:8px;margin-bottom:15px;display:none}
.msg-ok{background:#dcfce7;color:#166534;display:block}.msg-err{background:#fef2f2;color:#991b1b;display:block}
.upload-area{grid-column:1/-1;border:2px dashed #cbd5e1;border-radius:8px;padding:20px;text-align:center;cursor:pointer;transition:border 0.2s}
.upload-area:hover{border-color:#3b82f6}
.upload-area input{display:none}
.channel-badges{display:flex;gap:4px;flex-wrap:wrap}
@media(max-width:768px){.form-grid{grid-template-columns:1fr}.stats{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<div class="header">
    <h1>ArcisAI Sales Agent</h1>
    <span>AI-Powered Lead Management</span>
</div>
<div class="container">
    <div class="stats" id="stats">
        <div class="stat-card"><h3>Total Leads</h3><div class="num" id="s-total">0</div></div>
        <div class="stat-card"><h3>Emails Sent</h3><div class="num" id="s-sent">0</div></div>
        <div class="stat-card"><h3>WhatsApp Sent</h3><div class="num green" id="s-wa">0</div></div>
        <div class="stat-card"><h3>Avg Score</h3><div class="num" id="s-score">0</div></div>
        <div class="stat-card"><h3>Today</h3><div class="num" id="s-today">0</div></div>
    </div>

    <div class="card">
        <h2>Add New Lead</h2>
        <div id="msg"></div>
        <form id="leadForm" class="form-grid">
            <div><label>Full Name *</label><input name="name" required placeholder="e.g. Rajesh Kumar"></div>
            <div><label>Email *</label><input name="email" type="email" required placeholder="e.g. rajesh@company.com"></div>
            <div><label>Company</label><input name="company" placeholder="e.g. ABC Industries"></div>
            <div><label>Phone (for WhatsApp)</label><input name="phone" placeholder="e.g. +91 98765 43210"></div>
            <div><label>Customer Type</label>
                <select name="customer_type">
                    <option value="">Select...</option>
                    <option value="government">Government / PSU</option>
                    <option value="enterprise">Enterprise / Corporate</option>
                    <option value="si">System Integrator</option>
                    <option value="dealer">Dealer / Distributor</option>
                    <option value="residential">Residential</option>
                    <option value="other">Other</option>
                </select>
            </div>
            <div><label>Quantity</label><input name="quantity" placeholder="e.g. 50 cameras"></div>
            <textarea name="requirement" placeholder="Describe what they need... e.g. 50 bullet cameras for warehouse surveillance with night vision"></textarea>
            <div class="btn-row"><button type="submit" class="btn" id="submitBtn">Send Email + WhatsApp & Save Lead</button></div>
        </form>
    </div>

        <div class="card">
        <h2>Upload CSV of Leads — Auto Email + WhatsApp</h2>
        <p style="color:#666;font-size:14px;margin-bottom:10px">Upload your daily inbound leads CSV. The AI agent will <strong>automatically send personalized emails AND WhatsApp messages</strong> to every lead.</p>
        <p style="color:#888;font-size:13px;margin-bottom:12px">CSV format: <code style="background:#f1f5f9;padding:2px 6px;border-radius:4px">name, email, company, phone, requirement, customer_type</code>
        &nbsp; <a href="#" onclick="downloadSampleCSV();return false" style="color:#3b82f6;font-size:13px">Download Sample CSV</a></p>
        <div class="upload-area" id="uploadArea" onclick="document.getElementById('csvFile').click()">
            <input type="file" id="csvFile" accept=".csv" onchange="uploadCSV(this)">
            <p style="color:#666" id="uploadLabel">Click or drag CSV file here to upload & auto-fire messages</p>
        </div>
        <div id="csvProgress" style="display:none;margin-top:15px">
            <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                <span id="csvProgressText" style="font-size:14px;font-weight:600;color:#1e3a8a">Processing...</span>
                <span id="csvProgressCount" style="font-size:14px;color:#666">0 / 0</span>
            </div>
            <div style="background:#e2e8f0;border-radius:8px;height:12px;overflow:hidden">
                <div id="csvBar" style="background:linear-gradient(90deg,#3b82f6,#1e3a8a);height:100%;border-radius:8px;width:0%;transition:width 0.3s"></div>
            </div>
        </div>
        <div id="csvResults" style="display:none;margin-top:15px">
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px">
                <div style="background:#dcfce7;border-radius:8px;padding:10px;text-align:center"><div style="font-size:20px;font-weight:700;color:#166534" id="csvEmails">0</div><div style="font-size:12px;color:#166534">Emails Sent</div></div>
                <div style="background:#dcfce7;border-radius:8px;padding:10px;text-align:center"><div style="font-size:20px;font-weight:700;color:#166534" id="csvWA">0</div><div style="font-size:12px;color:#166534">WhatsApp Sent</div></div>
                <div style="background:#fef2f2;border-radius:8px;padding:10px;text-align:center"><div style="font-size:20px;font-weight:700;color:#991b1b" id="csvFailed">0</div><div style="font-size:12px;color:#991b1b">Failed</div></div>
                <div style="background:#f0f4f8;border-radius:8px;padding:10px;text-align:center"><div style="font-size:20px;font-weight:700;color:#1e3a8a" id="csvTotal">0</div><div style="font-size:12px;color:#1e3a8a">Total Rows</div></div>
            </div>
            <table class="leads-table" id="csvResultsTable" style="display:none">
                <thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Email Status</th><th>WhatsApp Status</th><th>Score</th></tr></thead>
                <tbody id="csvResultsBody"></tbody>
            </table>
            <div style="text-align:center;margin-top:10px"><a href="#" onclick="document.getElementById('csvResultsTable').style.display=document.getElementById('csvResultsTable').style.display==='none'?'table':'none';return false" style="color:#3b82f6;font-size:13px">Toggle row details</a></div>
        </div>
    </div>
<div class="card">
        <h2>Recent Leads</h2>
        <table class="leads-table">
            <thead><tr><th>Name</th><th>Email</th><th>Company</th><th>Score</th><th>Priority</th><th>Channels</th><th>Date</th></tr></thead>
            <tbody id="leadsBody"></tbody>
        </table>
    </div>
</div>

<script>
const API = '';
function showMsg(text, ok) {
    const m = document.getElementById('msg');
    m.textContent = text; m.className = 'msg ' + (ok ? 'msg-ok' : 'msg-err');
    setTimeout(() => m.className = 'msg', 6000);
}
document.getElementById('leadForm').onsubmit = async (e) => {
    e.preventDefault();
    const btn = document.getElementById('submitBtn');
    btn.disabled = true; btn.textContent = 'Sending...';
    const fd = new FormData(e.target);
    const data = Object.fromEntries(fd);
    try {
        const r = await fetch(API + '/api/lead', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(data)});
        const j = await r.json();
        if (j.success) {
            let msg = 'Lead saved! Email: ' + (j.lead.email_status || '?');
            if (j.lead.whatsapp_status) msg += ' | WhatsApp: ' + j.lead.whatsapp_status;
            showMsg(msg, true);
            e.target.reset(); loadLeads();
        } else showMsg('Error: ' + (j.error || 'Unknown'), false);
    } catch(err) { showMsg('Network error: ' + err.message, false); }
    btn.disabled = false; btn.textContent = 'Send Email + WhatsApp & Save Lead';
};
async function downloadSampleCSV() {
    const csv = 'name,email,company,phone,requirement,customer_type\\nRajesh Kumar,rajesh@techsol.in,TechSol Industries,+919876543210,50 bullet cameras for warehouse with night vision,si\\nPriya Mehta,priya@govproject.in,Gujarat Smart City,+919123456789,200 ANPR cameras for highway monitoring,government\\nAmit Shah,amit@securenet.com,SecureNet Dealers,+919555123456,Looking to become ArcisAI dealer in Rajasthan,dealer\\nSneha Patel,sneha@enterprise.co,Enterprise Corp,+919444567890,100 dome cameras for corporate office security,enterprise';
    const blob = new Blob([csv], {type: 'text/csv'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'arcisai_leads_sample.csv'; a.click();
}
async function uploadCSV(input) {
    const file = input.files[0]; if (!file) return;
    const text = await file.text();
    const lines = text.trim().split('\\n').slice(1).filter(l => l.trim());
    if (!lines.length) { showMsg('CSV is empty or has no data rows', false); return; }
    const total = lines.length;
    let emailsSent=0, waSent=0, failed=0, processed=0;
    const progDiv = document.getElementById('csvProgress');
    const bar = document.getElementById('csvBar');
    const pText = document.getElementById('csvProgressText');
    const pCount = document.getElementById('csvProgressCount');
    const resDiv = document.getElementById('csvResults');
    const resBody = document.getElementById('csvResultsBody');
    progDiv.style.display='block'; resDiv.style.display='none'; resBody.innerHTML='';
    document.getElementById('uploadArea').style.pointerEvents='none'; document.getElementById('uploadArea').style.opacity='0.5';
    document.getElementById('uploadLabel').textContent='Processing leads...';
    for (const line of lines) {
        const [name, email, company, phone, ...rest] = line.split(',').map(s => s.trim().replace(/^"|"$/g, ''));
        processed++;
        pText.textContent = 'Sending to ' + (name||email||'lead') + '...';
        pCount.textContent = processed + ' / ' + total;
        bar.style.width = Math.round(processed/total*100) + '%';
        if (!name || !email) {
            failed++;
            resBody.innerHTML += '<tr><td>'+(name||'-')+'</td><td>'+(email||'-')+'</td><td>-</td><td><span class=\"badge badge-failed\">Missing data</span></td><td>-</td><td>-</td></tr>';
            continue;
        }
        const requirement = rest.length > 1 ? rest.slice(0, -1).join(',') : (rest[0] || 'CCTV cameras');
        const customer_type = rest.length > 1 ? rest[rest.length - 1] : '';
        try {
            const r = await fetch(API + '/api/lead', {method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, email, company: company||'', phone: phone||'', requirement, customer_type})});
            const j = await r.json();
            if (j.success) {
                const es = j.lead.email_status||'?'; const ws = j.lead.whatsapp_status||'skipped';
                if (es==='sent') emailsSent++;
                if (ws==='sent') waSent++;
                const eBadge = es==='sent'?'badge-sent':'badge-failed';
                const wBadge = ws==='sent'?'badge-sent':ws==='skipped'?'badge-skipped':'badge-failed';
                resBody.innerHTML += '<tr><td>'+name+'</td><td>'+email+'</td><td>'+(phone||'-')+'</td><td><span class=\"badge '+eBadge+'\">'+es+'</span></td><td><span class=\"badge '+wBadge+'\">'+ws+'</span></td><td>'+(j.lead.score||0)+'</td></tr>';
            } else { failed++; resBody.innerHTML += '<tr><td>'+name+'</td><td>'+email+'</td><td>'+(phone||'-')+'</td><td><span class=\"badge badge-failed\">error</span></td><td>-</td><td>-</td></tr>'; }
        } catch(e) { failed++; resBody.innerHTML += '<tr><td>'+name+'</td><td>'+email+'</td><td>'+(phone||'-')+'</td><td><span class=\"badge badge-failed\">network error</span></td><td>-</td><td>-</td></tr>'; }
    }
    pText.textContent = 'Done!'; bar.style.width='100%'; bar.style.background='linear-gradient(90deg,#16a34a,#22c55e)';
    resDiv.style.display='block';
    document.getElementById('csvEmails').textContent=emailsSent;
    document.getElementById('csvWA').textContent=waSent;
    document.getElementById('csvFailed').textContent=failed;
    document.getElementById('csvTotal').textContent=total;
    document.getElementById('csvResultsTable').style.display='table';
    showMsg('CSV done! '+emailsSent+' emails + '+waSent+' WhatsApp sent to '+total+' leads', emailsSent>0);
    loadLeads(); input.value='';
    document.getElementById('uploadArea').style.pointerEvents='auto'; document.getElementById('uploadArea').style.opacity='1';
    document.getElementById('uploadLabel').textContent='Click or drag CSV file here to upload & auto-fire messages';
    setTimeout(()=>{bar.style.background='linear-gradient(90deg,#3b82f6,#1e3a8a)';},3000);
}
function loadLeads() {
    try {
        const r = await fetch(API + '/api/leads');
        const leads = await r.json();
        const tbody = document.getElementById('leadsBody');
        tbody.innerHTML = '';
        let emailSent=0, waSent=0, totalScore=0, today=0;
        const todayStr = new Date().toISOString().split('T')[0];
        leads.forEach(l => {
            const sc = l.score||0; totalScore += sc;
            if (l.email_status === 'sent') emailSent++;
            if (l.whatsapp_status === 'sent') waSent++;
            if ((l.created_at||'').startsWith(todayStr)) today++;
            const scClass = sc >= 75 ? 'score-high' : sc >= 50 ? 'score-med' : 'score-low';
            const prClass = (l.priority||'').toLowerCase().includes('high') ? 'badge-high' : (l.priority||'').toLowerCase().includes('med') ? 'badge-medium' : 'badge-normal';

            // Channel badges
            const emailBadge = l.email_status === 'sent' ? '<span class="badge badge-sent">Email</span>' :
                               l.email_status === 'failed' ? '<span class="badge badge-failed">Email</span>' : '';
            const waBadge = l.whatsapp_status === 'sent' ? '<span class="badge badge-sent">WhatsApp</span>' :
                            l.whatsapp_status === 'failed' ? '<span class="badge badge-failed">WA</span>' :
                            l.whatsapp_status === 'skipped' ? '<span class="badge badge-skipped">WA</span>' : '';

            tbody.innerHTML += `<tr><td><strong>${l.name||''}</strong></td><td>${l.email||''}</td><td>${l.company||'-'}</td>
                <td><span class="score ${scClass}">${sc}</span></td><td><span class="badge ${prClass}">${l.priority||'NORMAL'}</span></td>
                <td><div class="channel-badges">${emailBadge}${waBadge}</div></td><td>${(l.created_at||'').split('T')[0]}</td></tr>`;
        });
        document.getElementById('s-total').textContent = leads.length;
        document.getElementById('s-sent').textContent = emailSent;
        document.getElementById('s-wa').textContent = waSent;
        document.getElementById('s-score').textContent = leads.length ? Math.round(totalScore/leads.length) : 0;
        document.getElementById('s-today').textContent = today;
    } catch(e) { console.error(e); }
}
loadLeads();
</script>
</body>
</html>"""

# ============ API ROUTES ============
@app.route("/")
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route("/api/lead", methods=["POST"])
def add_lead():
    try:
        data = request.json
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        company = data.get("company", "").strip()
        phone = data.get("phone", "").strip()
        requirement = data.get("requirement", "CCTV cameras").strip()
        customer_type = data.get("customer_type", "").strip()
        quantity = data.get("quantity", "").strip()

        if not name or not email:
            return jsonify({"success": False, "error": "Name and email required"})

        # Score the lead
        full_req = f"{requirement} {quantity}".strip()
        score = score_lead(name, company, full_req, customer_type)
        first_name = name.split()[0] if name else "there"

        # Build and send email
        subject, html, priority = build_email_html(first_name, company, full_req, score, customer_type)
        email_status = "pending"
        try:
            send_email(email, subject, html)
            email_status = "sent"
        except Exception as e:
            email_status = f"failed: {str(e)}"

        # Send WhatsApp if phone number provided
        whatsapp_status = "skipped"
        whatsapp_detail = ""
        if phone:
            try:
                wa_msg = build_whatsapp_message(first_name, company, full_req, customer_type)
                success, detail = send_whatsapp_twilio(phone, wa_msg)
                whatsapp_status = "sent"
                whatsapp_detail = detail
            except Exception as e:
                whatsapp_status = f"failed: {str(e)}"
                whatsapp_detail = str(e)
        else:
            whatsapp_detail = "no phone number provided"

        # Save lead
        leads = load_leads()
        lead = {
            "id": str(uuid.uuid4())[:8],
            "name": name, "email": email, "company": company,
            "phone": phone, "requirement": full_req,
            "customer_type": customer_type, "quantity": quantity,
            "score": score, "priority": priority,
            "email_status": email_status.split(":")[0].strip(),
            "email_subject": subject,
            "whatsapp_status": whatsapp_status.split(":")[0].strip(),
            "whatsapp_detail": whatsapp_detail,
            "created_at": datetime.utcnow().isoformat(),
            "follow_up_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        leads.insert(0, lead)
        save_leads(leads)

        overall_success = email_status.startswith("sent")
        return jsonify({
            "success": overall_success,
            "lead": lead,
            "email_status": email_status,
            "whatsapp_status": whatsapp_status,
            "error": email_status if "failed" in email_status else None
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/leads")
def list_leads():
    return jsonify(load_leads())

@app.route("/api/health")
def health():
    return jsonify({
        "status": "running",
        "service": "ArcisAI Sales Agent",
        "channels": {
            "email": "resend" if RESEND_API_KEY else "smtp",
            "whatsapp": "twilio" if TWILIO_ACCOUNT_SID else "not configured"
        }
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
