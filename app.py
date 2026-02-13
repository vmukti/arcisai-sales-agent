"""
ArcisAI Independent AI Sales Agent - Web App
Deploy on Render.com: python app.py
Your team uploads leads â AI sends personalized emails automatically
"""
import os, json, smtplib, uuid, socket, urllib.request, urllib.error
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
    return min(score, 100)

def build_email_html(first_name, company, requirement, score, customer_type=""):
    """Build personalized email based on customer type — short, personal, action-oriented"""
    ct = (customer_type or "").lower()
    wa_link = "https://wa.me/919687779999"
    req_display = requirement or "security cameras"

    # Priority
    priority = "HIGH PRIORITY" if score >= 75 else "MEDIUM" if score >= 50 else "NORMAL"

    # Subject line — feels personal, not automated
    if company and company.lower() not in ["na", "none", "", "n/a"]:
        subject = f"Re: {company} \u2014 camera requirement"
    else:
        subject = f"Re: Your camera inquiry, {first_name}"

    # Company context for body
    co = f" for {company}" if company and company.lower() not in ["na", "none", "", "n/a"] else ""

    # Customer-type-specific paragraphs
    if ct == "si":
        p1 = f"Just saw your inquiry \u2014 {req_display}{co}. We can definitely help with this."
        p2 = "We work with 200+ SI partners across India and offer competitive project margins on our full AI camera range \u2014 ANPR, face recognition, crowd analytics, all with edge AI processing."
        p3 = "Happy to share the SI price list and discuss your project scope. Fastest way \u2014 drop me a WhatsApp message and I\u2019ll send it across right now:"
    elif ct == "dealer":
        p1 = f"Noted your interest in ArcisAI \u2014 {req_display}{co}."
        p2 = "We\u2019re actively expanding our dealer network and offer attractive margins with marketing support. Our AI cameras are 100% Made in India (non-Chinese SoC) \u2014 strong pull in current market."
        p3 = "I can share dealer pricing and current schemes. Just message me:"
    elif ct == "government":
        p1 = f"Thank you for your interest \u2014 {req_display}{co}."
        p2 = "Our cameras are STQC certified, 100% Made in India with non-Chinese SoC, and deployed across multiple smart city and government projects. We\u2019re GeM listed as well."
        p3 = "I can share compliance documents and project pricing. Let\u2019s connect:"
    elif ct == "enterprise":
        p1 = f"Saw your requirement \u2014 {req_display}{co}. This is right up our alley."
        p2 = "We\u2019ve deployed similar setups across factories, warehouses, and corporate campuses. Our edge AI cameras handle ANPR, intrusion detection, crowd analytics \u2014 all on-device, no heavy server needed."
        p3 = "Would love to understand your exact setup and share a tailored proposal:"
    elif ct == "residential":
        p1 = f"Thanks for checking out ArcisAI! I see you\u2019re interested in {req_display}{co}."
        p2 = "Our home security cameras come with AI-powered smart detection, night vision, and easy mobile app monitoring. We have options starting from budget-friendly to premium setups."
        p3 = "Happy to help you pick the right cameras for your home. Just message us:"
    else:
        p1 = f"Thanks for your interest in ArcisAI! I see you\u2019re looking at {req_display}{co}."
        p2 = "Our AI-powered cameras are designed and made in India, with smart detection, night vision, and remote monitoring built right in. We have options for every budget and scale."
        p3 = "Happy to help you find the right fit. Best way to connect:"

    html = f"""<html>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;line-height:1.7;color:#222;margin:0;padding:20px;">
<div style="max-width:560px;">
<p>Hi {first_name},</p>
<p>{p1}</p>
<p>{p2}</p>
<p>{p3}</p>
<p style="margin:20px 0;">
<a href="{wa_link}" style="background:#25D366;color:white;padding:12px 24px;text-decoration:none;border-radius:6px;font-weight:600;font-size:15px;">\u1f4ac WhatsApp Us</a>
&nbsp;&nbsp;or call <strong>+91 96877 79999</strong>
</p>
<p style="color:#555;font-size:14px;">Or just reply to this email \u2014 I\u2019ll get back within a few hours.</p>
<p style="margin-top:25px;padding-top:15px;border-top:1px solid #eee;">
Regards,<br><strong>ArcisAI Sales Team</strong><br>
<span style="color:#888;font-size:13px;"><a href="https://arcisai.io" style="color:#1e3a8a;">arcisai.io</a> \u00b7 India\u2019s AI-First CCTV Platform</span>
</p>
</div>
</body>
</html>"""

    return subject, html, priority

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
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:25px}
.stat-card{background:white;border-radius:12px;padding:20px;box-shadow:0 2px 8px rgba(0,0,0,0.08)}
.stat-card h3{font-size:14px;color:#666;margin-bottom:5px}.stat-card .num{font-size:32px;font-weight:700;color:#1e3a8a}
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
.badge-pending{background:#fef9c3;color:#854d0e}
.badge-high{background:#fee2e2;color:#991b1b}.badge-medium{background:#fef9c3;color:#854d0e}.badge-normal{background:#e0f2fe;color:#075985}
.score{font-weight:700;font-size:16px}
.score-high{color:#dc2626}.score-med{color:#d97706}.score-low{color:#2563eb}
.msg{padding:12px 16px;border-radius:8px;margin-bottom:15px;display:none}
.msg-ok{background:#dcfce7;color:#166534;display:block}.msg-err{background:#fef2f2;color:#991b1b;display:block}
.upload-area{grid-column:1/-1;border:2px dashed #cbd5e1;border-radius:8px;padding:20px;text-align:center;cursor:pointer;transition:border 0.2s}
.upload-area:hover{border-color:#3b82f6}
.upload-area input{display:none}
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
            <div><label>Phone</label><input name="phone" placeholder="e.g. +91 98765 43210"></div>
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
            <div class="btn-row"><button type="submit" class="btn" id="submitBtn">Send AI Email & Save Lead</button></div>
        </form>
    </div>

    <div class="card">
        <h2>Upload CSV of Leads</h2>
        <p style="color:#666;font-size:14px;margin-bottom:10px">CSV format: name, email, company, phone, requirement</p>
        <div class="upload-area" onclick="document.getElementById('csvFile').click()">
            <input type="file" id="csvFile" accept=".csv" onchange="uploadCSV(this)">
            <p style="color:#666">Click to upload CSV file</p>
        </div>
    </div>

    <div class="card">
        <h2>Recent Leads</h2>
        <table class="leads-table">
            <thead><tr><th>Name</th><th>Email</th><th>Company</th><th>Score</th><th>Priority</th><th>Status</th><th>Date</th></tr></thead>
            <tbody id="leadsBody"></tbody>
        </table>
    </div>
</div>

<script>
const API = '';
function showMsg(text, ok) {
    const m = document.getElementById('msg');
    m.textContent = text; m.className = 'msg ' + (ok ? 'msg-ok' : 'msg-err');
    setTimeout(() => m.className = 'msg', 5000);
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
        if (j.success) { showMsg('Lead saved & email sent to ' + data.email, true); e.target.reset(); loadLeads(); }
        else showMsg('Error: ' + (j.error || 'Unknown'), false);
    } catch(err) { showMsg('Network error: ' + err.message, false); }
    btn.disabled = false; btn.textContent = 'Send AI Email & Save Lead';
};
async function uploadCSV(input) {
    const file = input.files[0]; if (!file) return;
    const text = await file.text();
    const lines = text.trim().split('\\n').slice(1);
    let sent = 0, failed = 0;
    for (const line of lines) {
        const [name, email, company, phone, ...req] = line.split(',').map(s => s.trim().replace(/^"|"$/g, ''));
        if (!name || !email) { failed++; continue; }
        try {
            const r = await fetch(API + '/api/lead', {method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({name, email, company: company||'', phone: phone||'', requirement: req.join(',') || 'CCTV cameras'})});
            const j = await r.json();
            if (j.success) sent++; else failed++;
        } catch(e) { failed++; }
    }
    showMsg(`CSV processed: ${sent} emails sent, ${failed} failed`, sent > 0);
    loadLeads(); input.value = '';
}
async function loadLeads() {
    try {
        const r = await fetch(API + '/api/leads');
        const leads = await r.json();
        const tbody = document.getElementById('leadsBody');
        tbody.innerHTML = '';
        let sent=0, totalScore=0, today=0;
        const todayStr = new Date().toISOString().split('T')[0];
        leads.forEach(l => {
            const sc = l.score||0; totalScore += sc;
            if (l.email_status === 'sent') sent++;
            if ((l.created_at||'').startsWith(todayStr)) today++;
            const scClass = sc >= 75 ? 'score-high' : sc >= 50 ? 'score-med' : 'score-low';
            const prClass = (l.priority||'').toLowerCase().includes('high') ? 'badge-high' : (l.priority||'').toLowerCase().includes('med') ? 'badge-medium' : 'badge-normal';
            const stClass = l.email_status === 'sent' ? 'badge-sent' : l.email_status === 'failed' ? 'badge-failed' : 'badge-pending';
            tbody.innerHTML += `<tr><td><strong>${l.name||''}</strong></td><td>${l.email||''}</td><td>${l.company||'-'}</td>
                <td><span class="score ${scClass}">${sc}</span></td><td><span class="badge ${prClass}">${l.priority||'NORMAL'}</span></td>
                <td><span class="badge ${stClass}">${l.email_status||'pending'}</span></td><td>${(l.created_at||'').split('T')[0]}</td></tr>`;
        });
        document.getElementById('s-total').textContent = leads.length;
        document.getElementById('s-sent').textContent = sent;
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

        # Save lead
        leads = load_leads()
        lead = {
            "id": str(uuid.uuid4())[:8],
            "name": name, "email": email, "company": company,
            "phone": phone, "requirement": full_req,
            "customer_type": customer_type, "quantity": quantity,
            "score": score, "priority": priority,
            "email_status": email_status.split(":")[0],
            "email_subject": subject,
            "created_at": datetime.utcnow().isoformat(),
            "follow_up_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
        }
        leads.insert(0, lead)
        save_leads(leads)

        return jsonify({"success": email_status.startswith("sent"), "lead": lead, "error": email_status if "failed" in email_status else None})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/api/leads")
def list_leads():
    return jsonify(load_leads())

@app.route("/api/health")
def health():
    return jsonify({"status": "running", "service": "ArcisAI Sales Agent"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
