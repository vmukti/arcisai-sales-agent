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
ær·&WöF—7Æ—×¶6÷Òâv—fVâF†R7W'&VçB6ö×Æ–æ6R&WV—&VÖVçG2f÷"v÷fW&æÖVçB45Eb&ö7W&VÖVçBÂ’vçFVBFò&V6‚÷WBF—&V7FÇ’â ¢"Òb$gFW"F†RÔ„ÇS#—2Gf—6÷'’öâ6†–æW6RÖ÷&–v–â6ÖW&2Â6WfW&Âv÷fW&æÖVçB&ö¦V7G2†fRf6VBFVÆ—2&V6W6RfVæF÷'26÷VÆFåÇS#—B&÷f–FR&÷W"5E26W'F–f–6F–öâ÷"æöâÔ6†–æW6R6ô2Fö7VÖVçFF–öââvUÇS#—fR†VÇVB×VÇF—ÆRFW'FÖVçG2æf–vFRF†—26Öö÷F†Ç’â ¢2Òb#Ç7G&öæsä&6—4’—2gVÆÇ’&ö7W&VÖVçB×&VG“£Â÷7G&öæsãÆ'"óåÇS##"5E26W'F–f–VB†6W'F–f–6FRf–Æ&ÆR–ÖÖVF–FVÇ’“Æ'"óåÇS##"Æ—7FVBöâvTÒv—F‚7F—fR6B”CÆ'"óåÇS##"æöâÔ6†–æW6R6ô2ÇS#BRÖFR–â–æF–Æ'"óåÇS##"$•2Â•4ò#sÂ4RÂd426ö×Æ–çCÆ'"óåÇS##"‚VFvR’fVGW&W3¢å"Âf6RFWFV7F–öâÂ–çG'W6–öâÂf—&RÂRÂ7&÷vBæÇ—F–72ÂG&—v—&RÂÆö—FW&–æsÆ'"óåÇS##"FWÆ÷–VB7&÷726Ö'B6—G’ÂöÆ–6RÂFVfVæ6RÂæB5R&ö¦V7G2 ¢7FÒ$’6â6†&RF†R6ö×ÆWFR6ö×Æ–æ6RFö7VÖVçFF–öâ6¶vR…5E26W'F–f–6FRÂvTÒÆ—7F–ærÂ$•26W'F–f–6FRÂFV6†æ–6ÂFF6†VWB’&–v‡Bv’â6†ÆÂ’6VæBöâv†G4f÷"V–6²66W72Â÷"VÖ–Âv÷&·3ò ¢VÆ–b7BÓÒ&VçFW'&—6R# ¢Òb%6r–÷W"&WV—&VÖVçBf÷"·&WöF—7Æ—×¶6÷ÒÇS#BF†—2—2W†7FÇ’v†BvR7V6–Æ—¦R–ââ ¢"Òb$Ö÷7BVçFW'&—6W2vRv÷&²v—F‚vW&RV—F†W"––ærÆ¶‡2ÖöçF†Ç’f÷"6Æ÷VBÖ&6VBf–FVòæÇ—F–72F†EÇS#—26Æ÷ræB&—6W2FF&—f7’6öæ6W&ç2Â÷"W6–ær&6–26ÖW&2v—F‚¦W&ò–çFVÆÆ–vVæ6Râ&÷F‚6÷7BÖöæW’ÇS#BöæRF‡&÷Vv‚&–ÆÇ2ÂF†R÷F†W"F‡&÷Vv‚–æ6–FVçG2F†B6÷VÆB†fR&VVâ&WfVçFVBâ ¢2Òb#Ç7G&öæsä&6—4•ÇS#—2VFvR’6†ævW2F†—26ö×ÆWFVÇ“£Â÷7G&öæsãÆ'"óåÇS##"ÆÂ’&ö6W76–ær†Vç2öâÖ6ÖW&ÇS#BÃS×2ÆW'G2Â¦W&ò6Æ÷VB6÷7BÂRFF7F—2öâ×&VÖ—6SÆ'"óåÇS##"‚FWFV7F–öâG—W3¢–çG'W6–öâÂf—&RÂRÂå"Â7&÷vBÂf6RÂG&—v—&RÂÆö—FW&–æsÆ'"óåÇS##"66ÆW2g&öÒFò²6ÖW&2v—F‚6VçG&Æ—¦VBÖævVÖVçCÆ'"óåÇS##"S²VçFW'&—6RFWÆ÷–ÖVçG27&÷72–æF–†ÖçVf7GW&–ærÂv&V†÷W6W2Â†÷7—FÇ2Â6×W6W2’ ¢7FÒb$•ÇS#–BÆ÷fRFò6†÷r–÷RRÖÖ–âÆ—fRFVÖò7W7FöÖ—¦VBf÷"¶6õ÷6†÷'B÷"w–÷W"W6R66RwÒâ–÷UÇS#–ÆÂ6VRF†R’FWFV7F–öç2v÷&¶–ær–â&VÂ×F–ÖRâv†BF’v÷&·2F†—2vVV³ò ¢VÆ–b7BÓÒ'&W6–FVçF–Â# ¢Òb%F†æ·2f÷"–÷W"–çFW&W7B–â&6—4’6ÖW&7¶6÷Ò ¢"Òb$–b–÷UÇS#—&RÆöö¶–ærB6V7W&—G’6ÖW&2f÷"–÷W"†öÖR÷"6†÷Â–÷UÇS#—fR&ö&&Ç’6VVâGvòW‡G&VÖW2ÇS#B6†VÇS##“ƒ6ÖW&2F†BF–R–â2ÖöçF‡2Â÷"–×÷'FVB'&æG26†&v–ærÇS##“RÃ²W"6ÖW&âæV—F†W"Ö¶W26Vç6Râ ¢2Òb#Ç7G&öæsä÷W"V6òÕ6W&–W2†—G2F†R7vVWB7÷C£Â÷7G&öæsãÆ'"óåÇS##"’×÷vW&VB6ÖW&27F'F–ærBÇS##“2ÃSÆ'"óåÇS##"6Ö'BÆW'G2öâ–÷W"†öæR‡W'6öâFWFV7F–öâÂæ÷B§W7BÖ÷F–öâ“Æ'"óåÇS##"7'—7FÂ6ÆV"æ–v‡Bf—6–öâWFò3ÖWFW'3Æ'"óåÇS##"V7’Öö&–ÆRÇS#BvF6‚Æ—fRg&öÒç—v†W&SÆ'"óåÇS##"ÇVrÖæB×Æ’6WGWÂæòFV6†æ–6–âæVVFVBf÷"&6–2–ç7FÆÃÆ'"óåÇS##"ÖFR–â–æF–v—F‚"×–V"v'&çG’ ¢7FÒ$†÷rÖç’6ÖW&2&R–÷RF†–æ¶–æsòFVÆÂÖRF†R&V–÷RvçBFò6÷fW"æB•ÇS#–ÆÂ7VvvW7BF†R&W7B6¶vRv—F‚&–6–æröâv†G4â ¢VÇ6S ¢Òb$v÷B–÷W"–çV—'’&÷WB·&WöF—7Æ—×¶6÷ÒÇS#BF†æ·2f÷"6öç6–FW&–ær&6—4’â ¢"Òb%v†WF†W"–÷RæVVBB6ÖW&2÷"²ÂF†R6†ÆÆVævR—2F†R6ÖRÇS#Bf–æF–ær6ÖW&2F†B&R&VÆ–&ÆRÂ–çFVÆÆ–vVçBÂæB6ö×Æ–çBâÖ÷7B'&æG2V—F†W"Æ6²’fVGW&W2÷"6öÖRv—F‚6ö×Æ–æ6R&vvvRâ ¢2Òb#Ç7G&öæsä&6—4’6öÇfW2F†—3£Â÷7G&öæsãÆ'"óåÇS##"–æF–ÇS#—2Ö÷7BGfæ6VBVFvR’6ÖW&2ÇS#B‚FWFV7F–öâG—W2&ö6W76VBöâÖ6ÖW&Æ'"óåÇS##"2Õ6W&–W2‡&VÖ—VÒÂg&öÒÇS##“‚ÃS’æBV6òÕ6W&–W2‡fÇVRÂg&öÒÇS##“2ÃS“Æ'"óåÇS##"5E2²$•2²•4ò#s6W'F–f–VBÂÖFR–â–æF–Æ'"óåÇS##"BÖ6ÖW&†öÖR6WGW2Fò²6ÖW&VçFW'&—6RFWÆ÷–ÖVçG2 ¢7FÒ$•ÇS#–BÆ÷fRFòVæFW'7FæB–÷W"&WV—&VÖVçB&WGFW"âV–6²RÖÖ–â6ÆÂÂ÷"6†ÆÂ’6VæB&öGV7B6ö×&—6öâöâv†G4ò  ¢‡FÖÂÒb""#Æ‡FÖÃà£Æ&öG’7G–ÆSÒ&föçBÖfÖ–Ç“¢ÖÆR×7—7FVÒÂ&Æ–æ´Ö57—7FVÔföçBÂu6VvöRT’rÂ&ö&÷FòÂ6ç2×6W&–c²Æ–æRÖ†V–v‡C¢ãs²6öÆ÷#¢3333²Ö&v–ã¢²FF–æs¢²#à£ÆF—b7G–ÆSÒ&Ö‚×v–GFƒ¢cƒ²Ö&v–ã¢WFó²FF–æs¢#ƒ²#à¢Ç7G–ÆSÒ&föçB×6—¦S¢Wƒ²#ä†’¶f—'7EöæÖWÒÃÂ÷à¢Ç7G–ÆSÒ&föçB×6—¦S¢Wƒ²#ç·ÓÂ÷à¢Ç7G–ÆSÒ&föçB×6—¦S¢Wƒ²#ç·'ÓÂ÷à¢Ç7G–ÆSÒ&föçB×6—¦S¢Gƒ²#ç·7ÓÂ÷à¢Ç7G–ÆSÒ&föçB×6—¦S¢Wƒ²#ç¶7FÓÂ÷à¢ÆF—b7G–ÆSÒ&Ö&v–ã¢#W‚²#à¢Æ‡&VcÒ'·vöÆ–æ·Ò"7G–ÆSÒ&&6¶w&÷VæC¢3#TC3cc²6öÆ÷#¢v†—FS²FF–æs¢G‚3'ƒ²FW‡BÖFV6÷&F–öã¢æöæS²&÷&FW"×&F—W3¢‡ƒ²F—7Æ“¢–æÆ–æRÖ&Æö6³²föçB×vV–v‡C¢c²föçB×6—¦S¢Wƒ²#åÅScFcv†G4W2F—&V7FÇ“Âöà¢Ç7â7G–ÆSÒ&6öÆ÷#¢3ƒƒƒ²föçB×6—¦S¢7ƒ²Ö&v–âÖÆVgC¢ƒ²#æ÷"6ÆÂ³““cƒsrs““““Â÷7ãà¢ÂöF—cà¢Ç7G–ÆSÒ&Ö&v–ã¢²föçB×6—¦S¢Gƒ²#ä&W7B&Vv&G2ÃÂ÷à¢Ç7G–ÆSÒ&Ö&v–ã¢G‚²föçB×6—¦S¢Gƒ²#ãÇ7G&öæsä·W6†ÂÂ&6—4’6ÆW3Â÷7G&öæsãÂ÷à¢Ç7G–ÆSÒ&Ö&v–ã¢'‚²6öÆ÷#¢3ƒƒƒ²föçB×6—¦S¢7ƒ²#æ&6—6’æ–òÂ³““cƒsrs““““Â÷à£ÂöF—cà£Âö&öG“à£Âö‡FÖÃâ"" ¢&WGW&â7V&¦V7BÂ‡FÖÂÂ&–÷&—G ¢2ÓÓÓÓÓÓÓÓÓÓÓÒt„E4ÔU54tR%T”ÄDU"ÓÓÓÓÓÓÓÓÓÓÓĞ¦FVb'V–ÆE÷v†G6öÖW76vR†f—'7EöæÖRÂ6ö×ç’Â&WV—&VÖVçBÂ7W7FöÖW%÷G—SÒ""“ ¢""$'V–ÆB6†÷'BÂ6öçfW'6F–öæÂv†G4ÖW76vRf÷"–æF–â#$"Ö&¶WBÒÖ‚BÓRÆ–æW2"" ¢7BÒ†7W7FöÖW%÷G—R÷"""’æÆ÷vW"‚¢&W÷6†÷'BÒ‡&WV—&VÖVçB÷"'6V7W&—G’6ÖW&2"•³£cĞ¢6òÒb"‡¶6ö×ç—Ò’"–b6ö×ç’æB6ö×ç’æÆ÷vW"‚’æ÷B–â²&æ"Â&æöæR"Â""Â&âö%ÒVÇ6R"  ¢–b7BÓÒ'6’# ¢×6rÒb""$†’¶f—'7EöæÖWÒ¦—¶6÷ÒÅScCF  ¤v÷B–÷W"–çV—'’f÷"·&W÷6†÷'GÒà ¤&6—4’Ò5E26W'F–f–VB²‚’fVGW&W2öâÖ6ÖW&²æöâÔ6†–æW6R6ô2â#²4’'FæW'27&÷72–æF–Ç&VG’à ¥6†ÆÂ’6VæBF†R¥4’&–6RÆ—7B²Ö&v–âFWF–Ç2¢&–v‡B†W&Röâv†G4òÅScF6  ¥ÇS#B·W6†ÂÂ&6—4’Â&6—6’æ–ò"" ¢VÆ–b7BÓÒ&FVÆW"# ¢×6rÒb""$†’¶f—'7EöæÖWÒ¦—¶6÷ÒÅScCF  ¤&6—4’FVÆW"&öw&Ó ¥ÇS##"£CR²Ö&v–ç2¢„V6òÕ6W&–W2g&öÒÇS##“2ÃSÂ2Õ6W&–W2g&öÒÇS##“‚ÃS¥ÇS##"ÖFR–â–æF–Â5E26W'F–f–V@¥ÇS##"Ö&¶WF–ær¶—B²FVÖòVæ—G2–æ6ÇVFV@ ¥vUÇS#—&Röæ&ö&F–ær¦Æ–Ö—FVBFVÆW'2W"6—G’¢â–çFW&W7FVB–âF†R&–6RÆ—7CòÅScF6 ¥ÇS#B·W6†ÂÂ&6—4’Â&6—6’æ–ò"" ¢VÆ–b7BÓÒ&v÷fW&æÖVçB# ¢×6rÒb""$†’¶f—'7EöæÖWÒ¦—¶6÷ÒÅScCF  ¥&S¢·&W÷6†÷'GĞ ¤&6—4’—2¥5E26W'F–f–VB²vTÒÆ—7FVB²æöâÔ6†–æW6R6ô2²$•2²•4ò#s¢âgVÆÇ’6ö×Æ–çBf÷"v÷gB&ö7W&VÖVçBà ¤6â6†&RÆÂ6ö×Æ–æ6RFö72…5E26W'BÂvTÒFWF–Ç2ÂFF6†VWG2’&–v‡B†W&RâæVVBF†VÓòÅScF3@ ¥ÇS#B·W6†ÂÂ&6—4’Â&6—6’æ–ò"" ¢VÆ–b7BÓÒ&VçFW'&—6R# ¢×6rÒb""$†’¶f—'7EöæÖWÒ¦—¶6÷ÒÅScCF  ¥6r–÷W"&WV—&VÖVçBÇS#B·&W÷6†÷'GÒà ¤&6—4’Ò¤VFvR’öâÖ6ÖW&ÂÃS×2ÆW'G2Â¦W&ò6Æ÷VB6÷7B¢âS²6—FW2FWÆ÷–VB7&÷72–æF–à ¤6â’6†÷r–÷RV–6²RÖÖ–âFVÖò7W7FöÖ—¦VBf÷"–÷W"6WGWòÅSc6` ¥ÇS#B·W6†ÂÂ&6—4’Â&6—6’æ–ò"" ¢VÆ–b7BÓÒ'&W6–FVçF–Â# ¢×6rÒb""$†’¶f—'7EöæÖW×¶6÷ÒÅScCF  ¥F†æ·2f÷"–÷W"–çFW&W7B÷W"V6òÕ6W&–W2’6ÖW&27F'BB§W7B¥ÇS##“2ÃS¢ÇS#B6Ö'BÆW'G2Âæ–v‡Bf—6–öâÂÖö&–ÆR66W72à ¤†÷rÖç’6ÖW&2Fò–÷RæVVCò•ÇS#–ÆÂ6VæB–÷RF†R&W7B6¶vRv—F‚&–6–ærÅScFc ¥ÇS#B·W6†ÂÂ&6—4’Â&6—6’æ–ò"" ¢VÇ6S ¢×6rÒb""$†’¶f—'7EöæÖWÒ¦—¶6÷ÒÅScCF  ¤v÷B–÷W"–çV—'’&÷WB·&W÷6†÷'GÒâ&6—4’öffW'2–æF–ÇS#—2Ö÷7BGfæ6VB’6ÖW&2ÇS#B5E26W'F–f–VBÂÖFR–â–æF–ÂVFvR’&ö6W76–ærà ¤6â’6VæB–÷R&öGV7B6ö×&—6öâ²&–6–æröâv†G4òÅScF6  ¥ÇS#B·W6†ÂÂ&6—4’Â&6—6’æ–ò""  ¢&WGW&â×6p ¢2ÓÓÓÓÓÓÓÓÓÓÓÒt„E44TäDU"…Gv–Æ–ò$U5B’’ÓÓÓÓÓÓÓÓÓÓÓĞ¦FVbf÷&ÖE÷†öæUöf÷%÷v†G6‡†öæR“ ¢""$f÷&ÖB†öæRçVÖ&W"f÷"v†G4„RãcBf÷&ÖB’"" ¢–bæ÷B†öæS ¢&WGW&âæöæP¢2&VÖ÷fR76W2ÂF6†W2ÂF÷G2Â&VçF†W6W0¢6ÆVæVBÒ†öæRç7G&—‚’ç&WÆ6R‚""Â""’ç&WÆ6R‚"Ò"Â""’ç&WÆ6R‚"â"Â""’ç&WÆ6R‚"‚"Â""’ç&WÆ6R‚"’"Â""¢2&VÖ÷fRÆVF–ær²–b&W6VçB‡vRvÆÂFB—B&6²¢–b6ÆVæVBç7F'G7v—F‚‚"²"“ ¢6ÆVæVBÒ6ÆVæVE³¥Ğ¢2–b7F'G2v—F‚“æB—2"F–v—G2Â—Bw2–æF–à¢–b6ÆVæVBç7F'G7v—F‚‚#“"’æBÆVâ†6ÆVæVB’ÓÒ# ¢&WGW&âb"·¶6ÆVæVGÒ ¢2–bF–v—G2Â77VÖR–æF–âçVÖ&W ¢–bÆVâ†6ÆVæVB’ÓÒæB6ÆVæVE³Ò–â#csƒ’# ¢&WGW&âb"³“¶6ÆVæVGÒ ¢2–bÇ&VG’†26÷VçG'’6öFRƒ²F–v—G2¢–bÆVâ†6ÆVæVB’ãÒ ¢&WGW&âb"·¶6ÆVæVGÒ ¢&WGW&âæöæP ¦FVb6VæE÷v†G6÷Gv–Æ–ò‡Fõ÷†öæRÂÖW76vUö&öG’“ ¢""%6VæBv†G4ÖW76vRf–Gv–Æ–ò$U5B’W6–ærW&ÆÆ–"†æòW‡FW&æÂÆ–'&'’æVVFVB’"" ¢–bæ÷BEt”Ä”õô44õTåEõ4”B÷"æ÷BEt”Ä”õôUD…õDô´Tã ¢&—6RW†6WF–öâ‚%Gv–Æ–ò7&VFVçF–Ç2æ÷B6öæf–wW&VB" ¢f÷&ÖGFVE÷†öæRÒf÷&ÖE÷†öæUöf÷%÷v†G6‡Fõ÷†öæR¢–bæ÷Bf÷&ÖGFVE÷†öæS ¢&—6RW†6WF–öâ†b$–çfÆ–B†öæRçVÖ&W#¢·Fõ÷†öæWÒ" ¢2Gv–Æ–òÖW76vW2’VæGö–ç@¢W&ÂÒb&‡GG3¢òö’çGv–Æ–òæ6öÒó#ÓBÓô66÷VçG2÷µEt”Ä”õô44õTåEõ4”GÒôÖW76vW2æ§6öâ  ¢2&6–2WFƒ¢&6ScB…4”C¤WF…Fö¶Vâ¢WF…÷7G"Ò&6ScBæ#cFVæ6öFR†b'µEt”Ä”õô44õTåEõ4”GÓ§µEt”Ä”õôUD…õDô´TçÒ"æVæ6öFR‚’’æFV6öFR‚ ¢2f÷&ÒÖVæ6öFVB&öG’…Gv–Æ–òW6W2Æ–6F–öâ÷‚×wwrÖf÷&Ò×W&ÆVæ6öFVB¢–ÆöBÒW&ÆÆ–"ç'6RçW&ÆVæ6öFR‡°¢$g&öÒ#¢b'v†G6§µEt”Ä”õõt„E4ôe$ô×Ò"À¢%Fò#¢b'v†G6§¶f÷&ÖGFVE÷†öæWÒ"À¢$&öG’#¢ÖW76vUö&öG¢Ò’æVæ6öFR‚'WFbÓ‚" ¢&WÒW&ÆÆ–"ç&WVW7Bå&WVW7B€¢W&ÂÀ¢FF×–ÆöBÀ¢†VFW'3×°¢$WF†÷&—¦F–öâ#¢b$&6–2¶WF…÷7G'Ò"À¢$6öçFVçBÕG—R#¢&Æ–6F–öâ÷‚×wwrÖf÷&Ò×W&ÆVæ6öFVB"À¢%W6W"ÔvVçB#¢$&6—4’Õ6ÆW4vVçBóã ¢ÒÀ¢ÖWF†öCÒ%õ5B ¢ ¢G'“ ¢&W7ÒW&ÆÆ–"ç&WVW7BçW&Æ÷Vâ‡&WÂF–ÖV÷WCÓR¢&W7VÇBÒ§6öâæÆöG2‡&W7ç&VB‚’æFV6öFR‚’¢6–BÒ&W7VÇBævWB‚'6–B"Â""¢7FGW2Ò&W7VÇBævWB‚'7FGW2"Â""¢&WGW&âG'VRÂb'6VçB‡6–C¢·6–GÒÂ7FGW3¢·7FGW7Ò’ ¢W†6WBW&ÆÆ–"æW'&÷"ä…EEW'&÷"2S ¢&öG’ÒRç&VB‚’æFV6öFR‚¢&—6RW†6WF–öâ†b%Gv–Æ–ò’W'&÷"¶Ræ6öFWÓ¢¶&öG—Ò" ¢2ÓÓÓÓÓÓÓÓÓÓÓÒTÔ”Â4TäDU%2ÓÓÓÓÓÓÓÓÓÓÓĞ¦FVb6VæEöVÖ–Å÷&W6VæB‡FõöVÖ–ÂÂ7V&¦V7BÂ‡FÖÅö&öG’“ ¢""%6VæBVÖ–Âf–&W6VæB…EE’‡v÷&·2öâ&VæFW"g&VRF–W"’"" ¢–bæ÷B$U4TäEô•ô´U“ ¢&—6RW†6WF–öâ‚%$U4TäEô•ô´U’æ÷B6öæf–wW&VB"¢–ÆöBÒ§6öâæGV×2‡°¢&g&öÒ#¢b'´e$ôÕôäÔWÒÆöæ&ö&F–æt&W6VæBæFWcâ"À¢'Fò#¢·FõöVÖ–ÅÒÀ¢'7V&¦V7B#¢7V&¦V7BÀ¢&‡FÖÂ#¢‡FÖÅö&öG’À¢'&WÇ•÷Fò#¢4ÕEõU4U ¢Ò’æVæ6öFR‚'WFbÓ‚"¢&WÒW&ÆÆ–"ç&WVW7Bå&WVW7B€¢&‡GG3¢òö’ç&W6VæBæ6öÒöVÖ–Ç2"À¢FF×–ÆöBÀ¢†VFW'3×°¢$WF†÷&—¦F–öâ#¢b$&V&W"µ$U4TäEô•ô´U—Ò"À¢$6öçFVçBÕG—R#¢&Æ–6F–öâö§6öâ"À¢%W6W"ÔvVçB#¢$&6—4’Õ6ÆW4vVçBóã ¢ÒÀ¢ÖWF†öCÒ%õ5B ¢¢G'“ ¢&W7ÒW&ÆÆ–"ç&WVW7BçW&Æ÷Vâ‡&WÂF–ÖV÷WCÓ¢&W7VÇBÒ§6öâæÆöG2‡&W7ç&VB‚’æFV6öFR‚’¢&WGW&âG'VP¢W†6WBW&ÆÆ–"æW'&÷"ä…EEW'&÷"2S ¢&öG’ÒRç&VB‚’æFV6öFR‚¢&—6RW†6WF–öâ†b%&W6VæB’W'&÷"¶Ræ6öFWÓ¢¶&öG—Ò" ¦FVb6VæEöVÖ–Å÷6×G‡FõöVÖ–ÂÂ7V&¦V7BÂ‡FÖÅö&öG’“ ¢""%6VæBVÖ–Âf–4ÕE†f÷"6W'fW'2F†BÆÆ÷r÷WF&÷VæB4ÕE’"" ¢×6rÒÔ”ÔT×VÇF—'B‚&ÇFW&æF—fR"¢×6u²$g&öÒ%ÒÒb'´e$ôÕôäÔWÒÇµ4ÕEõU4U'Óâ ¢×6u²%Fò%ÒÒFõöVÖ–À¢×6u²%7V&¦V7B%ÒÒ7V&¦V7@¢×6u²%&WÇ’ÕFò%ÒÒ4ÕEõU4U ¢×6ræGF6‚„Ô”ÔUFW‡B†‡FÖÅö&öG’Â&‡FÖÂ"’¢W'&÷'2ÒµĞ¢f÷"ÖWF†öB–â²'76Â"Â'FÇ2%Ó ¢G'“ ¢–bÖWF†öBÓÒ'76Â# ¢6W'fW"Ò6×GÆ–"å4ÕEõ54Â…4ÕEô„õ5BÂCcRÂF–ÖV÷WCÓ‚¢VÇ6S ¢6W'fW"Ò6×GÆ–"å4ÕE…4ÕEô„õ5BÂSƒrÂF–ÖV÷WCÓ‚¢6W'fW"ç7F'GFÇ2‚¢6W'fW"æÆöv–â…4ÕEõU4U"Â4ÕEõ52¢6W'fW"ç6VæFÖ–Â…4ÕEõU4U"ÂFõöVÖ–ÂÂ×6ræ5÷7G&–ær‚’¢6W'fW"çV—B‚¢&WGW&âG'VP¢W†6WBW†6WF–öâ2S ¢W'&÷'2æVæB†b'¶ÖWF†öGÓ¢·7G"†R—Ò"¢&—6RW†6WF–öâ‚"Â"æ¦ö–â†W'&÷'2’ ¦FVb6VæEöVÖ–Â‡FõöVÖ–ÂÂ7V&¦V7BÂ‡FÖÅö&öG’“ ¢""%&÷WFRFò6÷'&V7BVÖ–Â&÷f–FW""" ¢–bTÔ”Åõ$õd”DU"ÓÒ'&W6VæB"æB$U4TäEô•ô´U“ ¢&WGW&â6VæEöVÖ–Å÷&W6VæB‡FõöVÖ–ÂÂ7V&¦V7BÂ‡FÖÅö&öG’¢VÆ–bTÔ”Åõ$õd”DU"ÓÒ'6×G# ¢&WGW&â6VæEöVÖ–Å÷6×G‡FõöVÖ–ÂÂ7V&¦V7BÂ‡FÖÅö&öG’¢VÇ6S ¢&—6RW†6WF–öâ‚$æòVÖ–Â&÷f–FW"6öæf–wW&VBâ6WB$U4TäEô•ô´U’÷"TÔ”Åõ$õd”DU#×6×G" ¢2ÓÓÓÓÓÓÓÓÓÓÓÒ…DÔÂDTÕÄDRÓÓÓÓÓÓÓÓÓÓÓĞ¤D4„$ô$Eô…DÔÂÒ""#ÂDô5E•R‡FÖÃà£Æ‡FÖÂÆæsÒ&Vâ#à£Æ†VCà£ÆÖWF6†'6WCÒ%UDbÓ‚#ãÆÖWFæÖSÒ'f–Ww÷'B"6öçFVçCÒ'v–GFƒÖFWf–6R×v–GF‚Â–æ—F–Â×66ÆSÓã#à£ÇF—FÆSä&6—4’6ÆW2vVçCÂ÷F—FÆSà£Ç7G–ÆSà¢§¶Ö&v–ã£·FF–æs£¶&÷‚×6—¦–æs¦&÷&FW"Ö&÷‡Ğ¦&öG—¶föçBÖfÖ–Ç“¢ÖÆR×7—7FVÒÄ&Æ–æ´Ö57—7FVÔföçBÂu6VvöRT’rÅ&ö&÷FòÇ6ç2×6W&–c¶&6¶w&÷VæC¢6ccFcƒ¶6öÆ÷#¢3337Ğ¢æ†VFW'¶&6¶w&÷VæC¦Æ–æV"Öw&F–VçBƒ3VFVrÂ3S6†Â36#ƒ&cb“¶6öÆ÷#§v†—FS·FF–æs£#‚3ƒ¶F—7Æ“¦fÆWƒ¶§W7F–g’Ö6öçFVçC§76RÖ&WGvVVã¶Æ–vâÖ—FV×3¦6VçFW'Ğ¢æ†VFW"ƒ¶föçB×6—¦S£#G‡Òæ†VFW"7ç¶föçB×6—¦S£Gƒ¶÷6—G“£ã‡Ğ¢æ6öçF–æW'¶Ö‚×v–GFƒ£#ƒ¶Ö&v–ã£#‚WFó·FF–æs£#‡Ğ¢ç7FG7¶F—7Æ“¦w&–C¶w&–B×FV×ÆFRÖ6öÇVÖç3§&WVB†WFòÖf—BÆÖ–æÖ‚ƒƒ‚Ãg"’“¶v£Wƒ¶Ö&v–âÖ&÷GFöÓ£#W‡Ğ¢ç7FBÖ6&G¶&6¶w&÷VæC§v†—FS¶&÷&FW"×&F—W3£'ƒ·FF–æs£#ƒ¶&÷‚×6†F÷s£'‚‡‚&v&ƒÃÃÃã‚—Ğ¢ç7FBÖ6&Bƒ7¶föçB×6—¦S£Gƒ¶6öÆ÷#¢3ccc¶Ö&v–âÖ&÷GFöÓ£W‡Òç7FBÖ6&BæçV×¶föçB×6—¦S£3'ƒ¶föçB×vV–v‡C£s¶6öÆ÷#¢3S6†Ğ¢ç7FBÖ6&BæçVÒæw&VVç¶6öÆ÷#¢3f3FĞ¢æ6&G¶&6¶w&÷VæC§v†—FS¶&÷&FW"×&F—W3£'ƒ·FF–æs£#Wƒ¶&÷‚×6†F÷s£'‚‡‚&v&ƒÃÃÃã‚“¶Ö&v–âÖ&÷GFöÓ£#‡Ğ¢æ6&Bƒ'¶6öÆ÷#¢3S6†¶Ö&v–âÖ&÷GFöÓ£Wƒ¶föçB×6—¦S£#‡Ğ¢æf÷&ÒÖw&–G¶F—7Æ“¦w&–C¶w&–B×FV×ÆFRÖ6öÇVÖç3£g"g#¶v£W‡Ğ¦Æ&VÇ¶F—7Æ“¦&Æö6³¶föçB×6—¦S£Gƒ¶föçB×vV–v‡C£c¶6öÆ÷#¢3SSS¶Ö&v–âÖ&÷GFöÓ£W‡Ğ¦–çWBÇ6VÆV7BÇFW‡F&V·v–GFƒ£S·FF–æs£‚Gƒ¶&÷&FW#£'‚6öÆ–B6S&S†c¶&÷&FW"×&F—W3£‡ƒ¶föçB×6—¦S£Gƒ·G&ç6—F–öã¦&÷&FW"ã'7Ğ¦–çWC¦fö7W2Ç6VÆV7C¦fö7W2ÇFW‡F&V¦fö7W7¶÷WFÆ–æS¦æöæS¶&÷&FW"Ö6öÆ÷#¢36#ƒ&cgĞ§FW‡F&V¶w&–BÖ6öÇVÖã£òÓ¶†V–v‡C£ƒƒ·&W6—¦S§fW'F–6ÇĞ¢æ'Fç¶&6¶w&÷VæC¢3S6†¶6öÆ÷#§v†—FS¶&÷&FW#¦æöæS·FF–æs£'‚3ƒ¶&÷&FW"×&F—W3£‡ƒ¶föçB×6—¦S£gƒ¶föçB×vV–v‡C£c¶7W'6÷#§ö–çFW#·G&ç6—F–öã¦&6¶w&÷VæBã'7Ğ¢æ'Fã¦†÷fW'¶&6¶w&÷VæC¢3SCgÒæ'Fã¦F—6&ÆVG¶&6¶w&÷VæC¢3“F6#ƒ¶7W'6÷#¦æ÷BÖÆÆ÷vVGĞ¢æ'Fâ×&÷w¶w&–BÖ6öÇVÖã£òÓ·FW‡BÖÆ–vã§&–v‡C¶Ö&v–â×F÷£W‡Ğ¢æÆVG2×F&ÆW·v–GFƒ£S¶&÷&FW"Ö6öÆÆ6S¦6öÆÆ6S¶Ö&v–â×F÷£‡Ğ¢æÆVG2×F&ÆRF‡¶&6¶w&÷VæC¢6c†ff3·FF–æs£'ƒ·FW‡BÖÆ–vã¦ÆVgC¶föçB×6—¦S£7ƒ¶6öÆ÷#¢3ccc¶&÷&FW"Ö&÷GFöÓ£'‚6öÆ–B6S&S†cĞ¢æÆVG2×F&ÆRFG·FF–æs£'ƒ¶&÷&FW"Ö&÷GFöÓ£‚6öÆ–B6ccVc“¶föçB×6—¦S£G‡Ğ¢æ&FvW¶F—7Æ“¦–æÆ–æRÖ&Æö6³·FF–æs£7‚ƒ¶&÷&FW"×&F—W3£'ƒ¶föçB×6—¦S£'ƒ¶föçB×vV–v‡C£cĞ¢æ&FvR×6VçG¶&6¶w&÷VæC¢6F6f6Ss¶6öÆ÷#¢3ccS3GÒæ&FvRÖf–ÆVG¶&6¶w&÷VæC¢6fVc&c#¶6öÆ÷#¢3““#'Ğ¢æ&FvR×VæF–æw¶&6¶w&÷VæC¢6fVc–33¶6öÆ÷#¢3ƒSFCWÒæ&FvR×6¶—VG¶&6¶w&÷VæC¢6ccVc“¶6öÆ÷#¢3cCsC†'Ğ¢æ&FvRÖ†–v‡¶&6¶w&÷VæC¢6fVS&S#¶6öÆ÷#¢3““#'Òæ&FvRÖÖVF—V×¶&6¶w&÷VæC¢6fVc–33¶6öÆ÷#¢3ƒSFCWÒæ&FvRÖæ÷&ÖÇ¶&6¶w&÷VæC¢6Sc&fS¶6öÆ÷#¢3sS“ƒWĞ¢ç66÷&W¶föçB×vV–v‡C£s¶föçB×6—¦S£g‡Ğ¢ç66÷&RÖ†–v‡¶6öÆ÷#¢6F3#c#gÒç66÷&RÖÖVG¶6öÆ÷#¢6C“ssgÒç66÷&RÖÆ÷w¶6öÆ÷#¢3#Sc6V'Ğ¢æ×6w·FF–æs£'‚gƒ¶&÷&FW"×&F—W3£‡ƒ¶Ö&v–âÖ&÷GFöÓ£Wƒ¶F—7Æ“¦æöæWĞ¢æ×6rÖö·¶&6¶w&÷VæC¢6F6f6Ss¶6öÆ÷#¢3ccS3C¶F—7Æ“¦&Æö6·Òæ×6rÖW''¶&6¶w&÷VæC¢6fVc&c#¶6öÆ÷#¢3““##¶F—7Æ“¦&Æö6·Ğ¢çWÆöBÖ&V¶w&–BÖ6öÇVÖã£òÓ¶&÷&FW#£'‚F6†VB66&CVS¶&÷&FW"×&F—W3£‡ƒ·FF–æs£3‚#ƒ·FW‡BÖÆ–vã¦6VçFW#¶7W'6÷#§ö–çFW#·G&ç6—F–öã¦ÆÂã'3·÷6—F–öã§&VÆF—fWĞ¢çWÆöBÖ&V¦†÷fW'¶&÷&FW"Ö6öÆ÷#¢36#ƒ&cc¶&6¶w&÷VæC¢6ccvfgĞ¢çWÆöBÖ&VæG&rÖ÷fW'¶&÷&FW"Ö6öÆ÷#¢36#ƒ&cc¶&6¶w&÷VæC¢6F&VfS¶&÷&FW"×v–GFƒ£7‡Ğ¢çWÆöBÖ&V–çWG¶F—7Æ“¦æöæWĞ¢æ6†ææVÂÖ&FvW7¶F—7Æ“¦fÆWƒ¶v£Gƒ¶fÆW‚×w&§w&Ğ¤ÖVF–†Ö‚×v–GFƒ£sc‡‚—²æf÷&ÒÖw&–G¶w&–B×FV×ÆFRÖ6öÇVÖç3£g'Òç7FG7¶w&–B×FV×ÆFRÖ6öÇVÖç3£g"g'×Ğ£Â÷7G–ÆSà£Âö†VCà£Æ&öG“à£ÆF—b6Æ73Ò&†VFW"#à¢Æƒä&6—4’6ÆW2vVçCÂöƒà¢Ç7ãä’Õ÷vW&VBÆVBÖævVÖVçCÂ÷7ãà£ÂöF—cà£ÆF—b6Æ73Ò&6öçF–æW"#à¢ÆF—b6Æ73Ò'7FG2"–CÒ'7FG2#à¢ÆF—b6Æ73Ò'7FBÖ6&B#ãÆƒ3åF÷FÂÆVG3Âöƒ3ãÆF—b6Æ73Ò&çVÒ"–CÒ'2×F÷FÂ#ãÂöF—cãÂöF—cà¢ÆF—b6Æ73Ò'7FBÖ6&B#ãÆƒ3äVÖ–Ç26VçCÂöƒ3ãÆF—b6Æ73Ò&çVÒ"–CÒ'2×6VçB#ãÂöF—cãÂöF—cà¢ÆF—b6Æ73Ò'7FBÖ6&B#ãÆƒ3åv†G46VçCÂöƒ3ãÆF—b6Æ73Ò&çVÒw&VVâ"–CÒ'2×v#ãÂöF—cãÂöF—cà¢ÆF—b6Æ73Ò'7FBÖ6&B#ãÆƒ3äfr66÷&SÂöƒ3ãÆF—b6Æ73Ò&çVÒ"–CÒ'2×66÷&R#ãÂöF—cãÂöF—cà¢ÆF—b6Æ73Ò'7FBÖ6&B#ãÆƒ3åFöF“Âöƒ3ãÆF—b6Æ73Ò&çVÒ"–CÒ'2×FöF’#ãÂöF—cãÂöF—cà¢ÂöF—cà ¢ÆF—b6Æ73Ò&6&B#à¢Æƒ#äFBæWrÆVCÂöƒ#à¢ÆF—b–CÒ&×6r#ãÂöF—cà¢Æf÷&Ò–CÒ&ÆVDf÷&Ò"6Æ73Ò&f÷&ÒÖw&–B#à¢ÆF—cãÆÆ&VÃägVÆÂæÖR£ÂöÆ&VÃãÆ–çWBæÖSÒ&æÖR"&WV—&VBÆ6V†öÆFW#Ò&Rærâ&¦W6‚·VÖ"#ãÂöF—cà¢ÆF—cãÆÆ&VÃäVÖ–Â£ÂöÆ&VÃãÆ–çWBæÖSÒ&VÖ–Â"G—SÒ&VÖ–Â"&WV—&VBÆ6V†öÆFW#Ò&Rærâ&¦W6„6ö×ç’æ6öÒ#ãÂöF—cà¢ÆF—cãÆÆ&VÃä6ö×ç“ÂöÆ&VÃãÆ–çWBæÖSÒ&6ö×ç’"Æ6V†öÆFW#Ò&Rærâ$2–æGW7G&–W2#ãÂöF—cà¢ÆF—cãÆÆ&VÃå†öæR†f÷"v†G4“ÂöÆ&VÃãÆ–çWBæÖSÒ'†öæR"Æ6V†öÆFW#Ò&Rærâ³““ƒscRC3##ãÂöF—cà¢ÆF—cãÆÆ&VÃä7W7FöÖW"G—SÂöÆ&VÃà¢Ç6VÆV7BæÖSÒ&7W7FöÖW%÷G—R#à¢Æ÷F–öâfÇVSÒ"#å6VÆV7BââãÂö÷F–öãà¢Æ÷F–öâfÇVSÒ&v÷fW&æÖVçB#äv÷fW&æÖVçBò5SÂö÷F–öãà¢Æ÷F–öâfÇVSÒ&VçFW'&—6R#äVçFW'&—6Rò6÷'÷&FSÂö÷F–öãà¢Æ÷F–öâfÇVSÒ'6’#å7—7FVÒ–çFVw&F÷#Âö÷F–öãà¢Æ÷F–öâfÇVSÒ&FVÆW"#äFVÆW"òF—7G&–'WF÷#Âö÷F–öãà¢Æ÷F–öâfÇVSÒ'&W6–FVçF–Â#å&W6–FVçF–ÃÂö÷F–öãà¢Æ÷F–öâfÇVSÒ&÷F†W"#ä÷F†W#Âö÷F–öãà¢Â÷6VÆV7Cà¢ÂöF—cà¢ÆF—cãÆÆ&VÃåVçF—G“ÂöÆ&VÃãÆ–çWBæÖSÒ'VçF—G’"Æ6V†öÆFW#Ò&RærâS6ÖW&2#ãÂöF—cà¢ÇFW‡F&VæÖSÒ'&WV—&VÖVçB"Æ6V†öÆFW#Ò$FW67&–&Rv†BF†W’æVVBâââRærâS'VÆÆWB6ÖW&2f÷"v&V†÷W6R7W'fV–ÆÆæ6Rv—F‚æ–v‡Bf—6–öâ#ãÂ÷FW‡F&Và¢ÆF—b6Æ73Ò&'Fâ×&÷r#ãÆ'WGFöâG—SÒ'7V&Ö—B"6Æ73Ò&'Fâ"–CÒ'7V&Ö—D'Fâ#å6VæBVÖ–Â²v†G4b6fRÆVCÂö'WGFöããÂöF—cà¢Âöf÷&Óà¢ÂöF—cà ¢ÆF—b6Æ73Ò&6&B#à¢Æƒ#åWÆöB55böbÆVG2(	BWFòVÖ–Â²v†G4Âöƒ#à¢Ç7G–ÆSÒ&6öÆ÷#¢3ccc¶föçB×6—¦S£Gƒ¶Ö&v–âÖ&÷GFöÓ£‚#åWÆöB–÷W"F–Ç’–æ&÷VæBÆVG255bâF†R’vVçBv–ÆÂÇ7G&öæsæWFöÖF–6ÆÇ’6VæBW'6öæÆ—¦VBVÖ–Ç2äBv†G4ÖW76vW3Â÷7G&öæsâFòWfW'’ÆVBãÂ÷à¢Ç7G–ÆSÒ&6öÆ÷#¢3ƒƒƒ¶föçB×6—¦S£7ƒ¶Ö&v–âÖ&÷GFöÓ£'‚#ä55bf÷&ÖC¢Æ6öFR7G–ÆSÒ&&6¶w&÷VæC¢6ccVc“·FF–æs£'‚gƒ¶&÷&FW"×&F—W3£G‚#ææÖRÂVÖ–ÂÂ6ö×ç’Â†öæRÂ&WV—&VÖVçBÂ7W7FöÖW%÷G—SÂö6öFSà¢fæ'7²Æ‡&VcÒ"2"öæ6Æ–6³Ò&F÷væÆöE6×ÆT55b‚“·&WGW&âfÇ6R"7G–ÆSÒ&6öÆ÷#¢36#ƒ&cc¶föçB×6—¦S£7‚#äF÷væÆöB6×ÆR55cÂöãÂ÷à¢ÆF—b6Æ73Ò'WÆöBÖ&V"–CÒ'WÆöD&V"öæ6Æ–6³Ò&Fö7VÖVçBævWDVÆVÖVçD'”–B‚v77df–ÆRr’æ6Æ–6²‚’ ¢öæG&v÷fW#Ò&WfVçBç&WfVçDFVfVÇB‚“¶WfVçBç7F÷&÷vF–öâ‚“·F†—2æ6Æ74Æ—7BæFB‚vG&rÖ÷fW"r’ ¢öæG&vÆVfSÒ&WfVçBç&WfVçDFVfVÇB‚“¶WfVçBç7F÷&÷vF–öâ‚“·F†—2æ6Æ74Æ—7Bç&VÖ÷fR‚vG&rÖ÷fW"r’ ¢öæG&÷Ò&WfVçBç&WfVçDFVfVÇB‚“¶WfVçBç7F÷&÷vF–öâ‚“·F†—2æ6Æ74Æ—7Bç&VÖ÷fR‚vG&rÖ÷fW"r“¶†æFÆTG&÷†WfVçB’#à¢Æ–çWBG—SÒ&f–ÆR"–CÒ&77df–ÆR"66WCÒ"æ77b"öæ6†ævSÒ'WÆöD55b‡F†—2’#à¢ÆF—b7G–ÆSÒ&föçB×6—¦S£3gƒ¶Ö&v–âÖ&÷GFöÓ£‡‚#ï	ù8CÂöF—cà¢Ç7G–ÆSÒ&6öÆ÷#¢3CCC¶föçB×vV–v‡C£c¶föçB×6—¦S£W‚"–CÒ'WÆöDÆ&VÂ#ä6Æ–6²†W&R÷"G&rbG&÷–÷W"55bf–ÆSÂ÷à¢Ç7G–ÆSÒ&6öÆ÷#¢3ƒƒƒ¶föçB×6—¦S£'ƒ¶Ö&v–â×F÷£G‚#ä66WG2æ77bf–ÆW2öæÇ“Â÷à¢ÂöF—cà¢ÆF—b–CÒ&77e&öw&W72"7G–ÆSÒ&F—7Æ“¦æöæS¶Ö&v–â×F÷£W‚#à¢ÆF—b7G–ÆSÒ&F—7Æ“¦fÆWƒ¶§W7F–g’Ö6öçFVçC§76RÖ&WGvVVã¶Ö&v–âÖ&÷GFöÓ£g‚#à¢Ç7â–CÒ&77e&öw&W75FW‡B"7G–ÆSÒ&föçB×6—¦S£Gƒ¶föçB×vV–v‡C£c¶6öÆ÷#¢3S6†#å&ö6W76–ærââãÂ÷7ãà¢Ç7â–CÒ&77e&öw&W746÷VçB"7G–ÆSÒ&föçB×6—¦S£Gƒ¶6öÆ÷#¢3ccb#ãòÂ÷7ãà¢ÂöF—cà¢ÆF—b7G–ÆSÒ&&6¶w&÷VæC¢6S&S†c¶&÷&FW"×&F—W3£‡ƒ¶†V–v‡C£'ƒ¶÷fW&fÆ÷s¦†–FFVâ#à¢ÆF—b–CÒ&77d&""7G–ÆSÒ&&6¶w&÷VæC¦Æ–æV"Öw&F–VçBƒ“FVrÂ36#ƒ&cbÂ3S6†“¶†V–v‡C£S¶&÷&FW"×&F—W3£‡ƒ·v–GFƒ£S·G&ç6—F–öã§v–GF‚ã72#ãÂöF—cà¢ÂöF—cà¢ÂöF—cà¢ÆF—b–CÒ&77e&W7VÇG2"7G–ÆSÒ&F—7Æ“¦æöæS¶Ö&v–â×F÷£W‚#à¢ÆF—b7G–ÆSÒ&F—7Æ“¦w&–C¶w&–B×FV×ÆFRÖ6öÇVÖç3§&WVBƒBÃg"“¶v£ƒ¶Ö&v–âÖ&÷GFöÓ£'‚#à¢ÆF—b7G–ÆSÒ&&6¶w&÷VæC¢6F6f6Ss¶&÷&FW"×&F—W3£‡ƒ·FF–æs£ƒ·FW‡BÖÆ–vã¦6VçFW"#ãÆF—b7G–ÆSÒ&föçB×6—¦S£#ƒ¶föçB×vV–v‡C£s¶6öÆ÷#¢3ccS3B"–CÒ&77dVÖ–Ç2#ãÂöF—cãÆF—b7G–ÆSÒ&föçB×6—¦S£'ƒ¶6öÆ÷#¢3ccS3B#äVÖ–Ç26VçCÂöF—cãÂöF—cà¢ÆF—b7G–ÆSÒ&&6¶w&÷VæC¢6F6f6Ss¶&÷&FW"×&F—W3£‡ƒ·FF–æs£ƒ·FW‡BÖÆ–vã¦6VçFW"#ãÆF—b7G–ÆSÒ&föçB×6—¦S£#ƒ¶föçB×vV–v‡C£s¶6öÆ÷#¢3ccS3B"–CÒ&77et#ãÂöF—cãÆF—b7G–ÆSÒ&föçB×6—¦S£'ƒ¶6öÆ÷#¢3ccS3B#åv†G46VçCÂöF—cãÂöF—cà¢ÆF—b7G–ÆSÒ&&6¶w&÷VæC¢6fVc&c#¶&÷&FW"×&F—W3£‡ƒ·FF–æs£ƒ·FW‡BÖÆ–vã¦6VçFW"#ãÆF—b7G–ÆSÒ&föçB×6—¦S£#ƒ¶föçB×vV–v‡C£s¶6öÆ÷#¢3““#""–CÒ&77df–ÆVB#ãÂöF—cãÆF—b7G–ÆSÒ&föçB×6—¦S£'ƒ¶6öÆ÷#¢3““#"#äf–ÆVCÂöF—cãÂöF—cà¢ÆF—b7G–ÆSÒ&&6¶w&÷VæC¢6ccFcƒ¶&÷&FW"×&F—W3£‡ƒ·FF–æs£ƒ·FW‡BÖÆ–vã¦6VçFW"#ãÆF—b7G–ÆSÒ&föçB×6—¦S£#ƒ¶föçB×vV–v‡C£s¶6öÆ÷#¢3S6†"–CÒ&77eF÷FÂ#ãÂöF—cãÆF—b7G–ÆSÒ&föçB×6—¦S£'ƒ¶6öÆ÷#¢3S6†#åF÷FÂ&÷w3ÂöF—cãÂöF—cà¢ÂöF—cà¢ÇF&ÆR6Æ73Ò&ÆVG2×F&ÆR"–CÒ&77e&W7VÇG5F&ÆR"7G–ÆSÒ&F—7Æ“¦æöæR#à¢ÇF†VCãÇG#ãÇFƒäæÖSÂ÷FƒãÇFƒäVÖ–ÃÂ÷FƒãÇFƒå†öæSÂ÷FƒãÇFƒäVÖ–Â7FGW3Â÷FƒãÇFƒåv†G47FGW3Â÷FƒãÇFƒå66÷&SÂ÷FƒãÂ÷G#ãÂ÷F†VCà¢ÇF&öG’–CÒ&77e&W7VÇG4&öG’#ãÂ÷F&öG“à¢Â÷F&ÆSà¢ÆF—b7G–ÆSÒ'FW‡BÖÆ–vã¦6VçFW#¶Ö&v–â×F÷£‚#ãÆ‡&VcÒ"2"öæ6Æ–6³Ò&Fö7VÖVçBævWDVÆVÖVçD'”–B‚v77e&W7VÇG5F&ÆRr’ç7G–ÆRæF—7Æ“ÖFö7VÖVçBævWDVÆVÖVçD'”–B‚v77e&W7VÇG5F&ÆRr’ç7G–ÆRæF—7Æ“ÓÓÒvæöæRsòwF&ÆRs¢væöæRs·&WGW&âfÇ6R"7G–ÆSÒ&6öÆ÷#¢36#ƒ&cc¶föçB×6—¦S£7‚#åFövvÆR&÷rFWF–Ç3ÂöãÂöF—cà¢ÂöF—cà¢ÂöF—cà ¢ÆF—b6Æ73Ò&6&B#à¢Æƒ#å&V6VçBÆVG3Âöƒ#à¢ÇF&ÆR6Æ73Ò&ÆVG2×F&ÆR#à¢ÇF†VCãÇG#ãÇFƒäæÖSÂ÷FƒãÇFƒäVÖ–ÃÂ÷FƒãÇFƒä6ö×ç“Â÷FƒãÇFƒå66÷&SÂ÷FƒãÇFƒå&–÷&—G“Â÷FƒãÇFƒä6†ææVÇ3Â÷FƒãÇFƒäFFSÂ÷FƒãÂ÷G#ãÂ÷F†VCà¢ÇF&öG’–CÒ&ÆVG4&öG’#ãÂ÷F&öG“à¢Â÷F&ÆSà¢ÂöF—cà£ÂöF—cà £Ç67&—Cà¦6öç7B’Òrs°¦gVæ7F–öâ6†÷t×6r‡FW‡BÂö²’°¢6öç7BÒÒFö7VÖVçBævWDVÆVÖVçD'”–B‚v×6rr“°¢ÒçFW‡D6öçFVçBÒFW‡C²Òæ6Æ74æÖRÒv×6rr²†ö²òv×6rÖö²r¢v×6rÖW'"r“°¢6WEF–ÖV÷WB‚‚’ÓâÒæ6Æ74æÖRÒv×6rrÂc“°§Ğ¦Fö7VÖVçBævWDVÆVÖVçD'”–B‚vÆVDf÷&Òr’æöç7V&Ö—BÒ7–æ2†R’Óâ°¢Rç&WfVçDFVfVÇB‚“°¢6öç7B'FâÒFö7VÖVçBævWDVÆVÖVçD'”–B‚w7V&Ö—D'Fâr“°¢'FâæF—6&ÆVBÒG'VS²'FâçFW‡D6öçFVçBÒu6VæF–ærâââs°¢6öç7BfBÒæWrf÷&ÔFF†RçF&vWB“°¢6öç7BFFÒö&¦V7Bæg&öÔVçG&–W2†fB“°¢G'’°¢6öç7B"Òv—BfWF6‚„’²rö’öÆVBrÂ¶ÖWF†öC¢uõ5BrÂ†VFW'3¢²t6öçFVçBÕG—Rs¢vÆ–6F–öâö§6öâwÒÂ&öG“¢¥4ôâç7G&–æv–g’†FF—Ò“°¢6öç7B¢Òv—B"æ§6öâ‚“°¢–b†¢ç7V66W72’°¢ÆWB×6rÒtÆVB6fVBVÖ–Ã¢r²†¢æÆVBæVÖ–Å÷7FGW2ÇÂsòr“°¢–b†¢æÆVBçv†G6÷7FGW2’×6r³ÒrÂv†G4¢r²¢æÆVBçv†G6÷7FGW3°¢6†÷t×6r†×6rÂG'VR“°¢RçF&vWBç&W6WB‚“²ÆöDÆVG2‚“°¢ÒVÇ6R6†÷t×6r‚tW'&÷#¢r²†¢æW'&÷"ÇÂuVæ¶æ÷vâr’ÂfÇ6R“°¢Ò6F6‚†W'"’²6†÷t×6r‚tæWGv÷&²W'&÷#¢r²W'"æÖW76vRÂfÇ6R“²Ğ¢'FâæF—6&ÆVBÒfÇ6S²'FâçFW‡D6öçFVçBÒu6VæBVÖ–Â²v†G4b6fRÆVBs°§Ó°¦gVæ7F–öâF÷væÆöE6×ÆT55b‚’°¢6öç7B77bÒvæÖRÆVÖ–ÂÆ6ö×ç’Ç†öæRÇ&WV—&VÖVçBÆ7W7FöÖW%÷G—UÅÆå&¦W6‚·VÖ"Ç&¦W6„FV6‡6öÂæ–âÅFV6…6öÂ–æGW7G&–W2Â³““ƒscSC3#ÃS'VÆÆWB6ÖW&2f÷"v&V†÷W6Rv—F‚æ–v‡Bf—6–öâÇ6•ÅÆå&—–ÖV‡FÇ&—–v÷g&ö¦V7Bæ–âÄwV¦&B6Ö'B6—G’Â³““#3CScsƒ’Ã#å"6ÖW&2f÷"†–v‡v’Ööæ—F÷&–ærÆv÷fW&æÖVçEÅÆäÖ—B6†‚ÆÖ—D6V7W&VæWBæ6öÒÅ6V7W&TæWBFVÆW'2Â³““SSS#3CSbÄÆöö¶–ærFò&V6öÖR&6—4’FVÆW"–â&¦7F†âÆFVÆW%ÅÆå6æV†FVÂÇ6æV†VçFW'&—6Ræ6òÄVçFW'&—6R6÷ <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:12px">
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
function downloadSampleCSV() {
    const csv = 'name,email,company,phone,requirement,customer_type\\nRajesh Kumar,rajesh@techsol.in,TechSol Industries,+919876543210,50 bullet cameras for warehouse with night vision,si\\nPriya Mehta,priya@govproject.in,Gujarat Smart City,+919123456789,200 ANPR cameras for highway monitoring,government\\nAmit Shah,amit@securenet.com,SecureNet Dealers,+919555123456,Looking to become ArcisAI dealer in Rajasthan,dealer\\nSneha Patel,sneha@enterprise.co,Enterprise Corp,+919444567890,100 dome cameras for corporate office security,enterprise';
    const blob = new Blob([csv], {type: 'text/csv'});
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'arcisai_leads_sample.csv'; a.click();
}
function handleDrop(e) {
    const dt = e.dataTransfer;
    if (dt.files && dt.files.length > 0) {
        const file = dt.files[0];
        if (!file.name.toLowerCase().endsWith('.csv')) {
            showMsg('Please upload a .csv file only', false);
            return;
        }
        processCSVFile(file);
    }
}
async function uploadCSV(input) {
    const file = input.files[0]; if (!file) return;
    processCSVFile(file);
}
async function processCSVFile(file) {
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
    loadLeads(); document.getElementById('csvFile').value='';
    document.getElementById('uploadArea').style.pointerEvents='auto'; document.getElementById('uploadArea').style.opacity='1';
    document.getElementById('uploadLabel').textContent='Click here or drag & drop your CSV file';
    setTimeout(()=>{bar.style.background='linear-gradient(90deg,#3b82f6,#1e3a8a)';},3000);
}
async function loadLeads() {
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
