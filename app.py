import streamlit as st
import pandas as pd
import requests
import os
import re
import json
from datetime import datetime, timedelta
import hashlib

====================== SECURE API KEYS ======================
if "NEWS_API_KEY" not in st.secrets:
st.error("⚠️ NEWS_API_KEY not found in secrets.")
st.stop()

NEWS_API_KEY = st.secrets["NEWS_API_KEY"]
MEDIASTACK_API_KEY = st.secrets.get("MEDIASTACK_API_KEY", "")

CSV_FILE = "political_retractions.csv"
USAGE_FILE = "mediastack_usage.json"
MEDIASTACK_FREE_CAP = 100

REQUIRED_COLS = [
"ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
"Original_Claim", "Correction", "Link", "Source", "Views_Estimate"
]

==================== Optimized Filtering Logic ====================
RETRACTION_WORDS = [
r"\bretract(?:s|ed|ion|ing)?\b",
r"\bcorrect(?:s|ed|ion|ing)?\b",
r"\berratum\b|\berrata\b",
r"\bwe regret\b",
r"\bclarif(?:y|ies|ied|ication)\b",
r"\bapolog(?:y|ize|ized|izes|izing)\b",
r"\bwalk(?:s|ed|ing)? back\b",
r"\bissues? a correction\b",
r"\bpulled? the (?:story|article|report)\b",
r"\bupdated? (?:our|this) story\b",
]

MEDIA_SELF_WORDS = [
r"\b(our|we|the (?:times|post|journal|cnn|nbc|abc|fox|ap|reuters|politico|bloomberg)) "
r"(?:correct|retract|clarif|apolog|regret|walk back|update|pull)\b",
]

POLITICS_WORDS = [
# Tier 1 - Highest priority
"trump", "biden", "harris", "kamala", "vance", "jd vance", "j.d. vance",
"newsom", "gavin newsom", "warren", "elizabeth warren",
"abbott", "greg abbott",

# Tier 2 - Requested additions
"rfk", "rfk jr", "robert kennedy", "tulsi gabbard", "gabbard",
"ted lieu", "lieu",

# Tier 3 - Other high-profile
"thune", "john thune", "cornyn", "john cornyn",
"schumer", "mcconnell", "pelosi", "aoc", "ocasio", "rubio", "desantis",

# Broad political terms (very important)
"election", "white house", "potus", "congress", "senate",
"house of representatives", "administration", "impeach",
"indictment", "scandal", "campaign"
]

FALSE_POSITIVE_PATTERNS = [
r"market correction", r"stock.*correct", r"course correction",
r"no regrets?", r"i don'?t regret", r"corrective (?:exercise|surgery|lens)",
r"retractable", r"spinal correction", r"posture correction",
r"whoopi", r"goldberg", r"celebrity", r"actor", r"study", r"research", r"covid",
r"clarifies? (his|her|their) comments?", r"trump clarifies",
]

RETRACTION_RE = re.compile("|".join(RETRACTION_WORDS), re.IGNORECASE)
MEDIA_SELF_RE = re.compile("|".join(MEDIA_SELF_WORDS), re.IGNORECASE)
FALSE_POSITIVE_RE = re.compile("|".join(FALSE_POSITIVE_PATTERNS), re.IGNORECASE)

def is_genuine_retraction(title: str, description: str) -> bool:
if not title:
return False
blob = f"{title} {description or ''}".lower()

if FALSE_POSITIVE_RE.search(blob):
return False
if not RETRACTION_RE.search(title):
return False
if not MEDIA_SELF_RE.search(blob):
return False
if not any(k in blob for k in POLITICS_WORDS):
return False
return True

def categorize_politics(text):
text = str(text).lower()
national = {
"trump", "biden", "harris", "kamala", "vance", "jd vance", "j.d. vance",
"newsom", "gavin newsom", "warren", "elizabeth warren",
"abbott", "greg abbott", "rfk", "robert kennedy", "tulsi gabbard", "gabbard",
"ted lieu", "lieu", "thune", "cornyn", "schumer", "mcconnell", "pelosi",
"aoc", "rubio", "desantis"
}
state = {
"sacramento", "san francisco", "denver", "chicago", "california",
"texas", "new york", "florida", "governor", "state legislature",
"city council", "mayor"
}

if any(k in text for k in national):
return "National"
elif any(k in text for k in state):
return "State"
return "Global/International"

==================== Storage helpers ====================
def generate_id(title, date):
clean_title = str(title).strip()
clean_date = str(date).strip()
return hashlib.md5(f"{clean_title}{clean_date}".encode("utf-8")).hexdigest()[:12]

def load_data():
if os.path.exists(CSV_FILE):
df = pd.read_csv(CSV_FILE)
for col in REQUIRED_COLS:
if col not in df.columns:
df[col] = "" if col in ["Original_Claim", "Correction", "Source", "Views_Estimate"] else None
return df
df = pd.DataFrame(columns=REQUIRED_COLS)
df.to_csv(CSV_FILE, index=False)
return df

def save_data(df):
df.to_csv(CSV_FILE, index=False)

def load_usage():
if os.path.exists(USAGE_FILE):
with open(USAGE_FILE, "r") as f:
data = json.load(f)
current_month = datetime.now().strftime("%Y-%m")
if data.get("month") != current_month:
data = {"month": current_month, "calls": 0}
return data
return {"month": datetime.now().strftime("%Y-%m"), "calls": 0}

def record_usage(n_calls=1):
data = load_usage()
data["calls"] += n_calls
with open(USAGE_FILE, "w") as f:
json.dump(data, f)
return data

def safe_format_date(date_str):
try:
return datetime.strptime(date_str[:10], "%Y-%m-%d").strftime("%b %d, %Y")
except Exception:
return date_str[:10] if date_str else ""

==================== Sources ====================
@st.cache_data(ttl=3600)
def fetch_newsapi(days_back=30):
since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
query = (
'(retraction OR correction OR erratum OR "we regret" OR clarifies OR corrected '
'OR "false report" OR apologizes OR "walks back") '
'AND (trump OR biden OR harris OR vance OR newsom OR warren OR abbott OR '
'rfk OR gabbard OR lieu OR election OR congress)'
)
url = f"https://newsapi.org/v2/everything?q={query}&language=en&from={since}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"

try:
resp = requests.get(url, timeout=20)
resp.raise_for_status()
articles = resp.json().get("articles", [])

rows = []
for art in articles:
title = art.get("title", "")
desc = art.get("description", "") or ""
if not is_genuine_retraction(title, desc):
continue

cat = categorize_politics(title + " " + desc)
published = art.get("publishedAt", "") or ""

rows.append({
"ID": generate_id(title, published),
"Date": published[:10],
"Formatted_Date": safe_format_date(published),
"Title": title,
"Outlet": art.get("source", {}).get("name", "Unknown"),
"Category": cat,
"Original_Claim": desc.split("—")[0].strip() if "—" in desc else "Original story referenced in retraction (see link)",
"Correction": desc or "Full correction at link",
"Link": art.get("url"),
"Source": "NewsAPI",
"Views_Estimate": "N/A",
})
return pd.DataFrame(rows)
except Exception as e:
st.error(f"NewsAPI error: {e}")
return pd.DataFrame()

@st.cache_data(ttl=3600)
def fetch_mediastack(days_back=30):
if not MEDIASTACK_API_KEY:
return pd.DataFrame(), 0

since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
keywords = "retraction,correction,trump,biden,harris,vance,newsom,warren,rfk,gabbard,lieu,election"

url = (
f"http://api.mediastack.com/v1/news?access_key={MEDIASTACK_API_KEY}"
f"&keywords={keywords}&languages=en&date={since},{datetime.now().strftime('%Y-%m-%d')}&limit=100"
)

try:
resp = requests.get(url, timeout=20)
resp.raise_for_status()
payload = resp.json()
if "error" in payload:
st.warning(f"Mediastack: {payload['error'].get('message')}")
return pd.DataFrame(), 1

articles = payload.get("data", [])
rows = []
for art in articles:
title = art.get("title", "")
desc = art.get("description", "") or ""
if not is_genuine_retraction(title, desc):
continue

cat = categorize_politics(title + " " + desc)
published = art.get("published_at", "") or ""

rows.append({
"ID": generate_id(title, published),
"Date": published[:10],
"Formatted_Date": safe_format_date(published),
"Title": title,
"Outlet": art.get("source", "Unknown"),
"Category": cat,
"Original_Claim": desc.split("—")[0].strip() if "—" in desc else "Original story referenced in retraction (see link)",
"Correction": desc or "Full correction at link",
"Link": art.get("url"),
"Source": "Mediastack",
"Views_Estimate": "N/A",
})
return pd.DataFrame(rows), 1
except Exception as e:
st.error(f"Mediastack error: {e}")
return pd.DataFrame(), 1

def fetch_all(days_back=30):
newsapi_df = fetch_newsapi(days_back=days_back)
mediastack_df, calls_used = fetch_mediastack(days_back=days_back)
if calls_used:
record_usage(calls_used)
combined = pd.concat([newsapi_df, mediastack_df], ignore_index=True)
return combined

==================== APP ====================
st.set_page_config(page_title="Political Retractions Tracker", layout="wide", page_icon="📰")

st.markdown("""
<style>
.block-container { padding-top: 2rem; }
.card {
background: #ffffff;
border: 1px solid #e6e6e6;
border-radius: 10px;
padding: 16px 18px;
margin-bottom: 14px;
box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.card-meta { color: #6b7280; font-size: 0.8rem; margin-bottom: 8px; }
.card-title { font-size: 1.0rem; font-weight: 600; margin: 12px 0; line-height: 1.3; }
.card-title a { color: #111827; text-decoration: none; }
.card-title a:hover { text-decoration: underline; }
.tag {
display: inline-block;
font-size: 0.72rem;
font-weight: 600;
padding: 2px 8px;
border-radius: 999px;
margin-bottom: 12px;
}
.tag-correction { background: #fee2e2; color: #991b1b; }
.section-label { font-size: 0.75rem; font-weight: 700; color: #374151; text-transform: uppercase; letter-spacing: 0.03em; margin-top: 8px; }
.card-source { color: #9ca3af; font-size: 0.72rem; margin-top: 12px; }
</style>
""", unsafe_allow_html=True)

st.title("📰 Political Retractions & Corrections Tracker")
st.markdown("Daily catalog of media self-retractions & corrections • Newest on top")

df = load_data()
usage = load_usage()

---------------- Sidebar ----------------
st.sidebar.header("🔄 Automation")

if st.sidebar.button("🔍 Search for New Retractions Now", type="primary", use_container_width=True):
with st.spinner("Searching NewsAPI + Mediastack..."):
new_df = fetch_all(days_back=30)
if not new_df.empty:
combined = pd.concat([df, new_df]).drop_duplicates(subset=["ID"])
added = len(combined) - len(df)
save_data(combined)
st.sidebar.success(f"✅ Added {added} new entries!")
st.rerun()
else:
st.sidebar.info("No new matches found this run.")

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Source status")
st.sidebar.caption("NewsAPI: configured ✅")
if MEDIASTACK_API_KEY:
pct = min(usage["calls"] / MEDIASTACK_FREE_CAP, 1.0)
st.sidebar.caption("Mediastack: configured ✅")
st.sidebar.progress(pct, text=f"{usage['calls']} / {MEDIASTACK_FREE_CAP} calls used")
else:
st.sidebar.caption("Mediastack: not configured (optional)")

st.sidebar.markdown("---")
st.sidebar.subheader("🔧 Filters")
days_filter = st.sidebar.slider("Show entries from the last N days", 1, 90, 30)
outlet_filter = st.sidebar.text_input("Filter by outlet (optional)", "")

---------------- Main Display ----------------
st.subheader("Recent Retractions & Corrections")

if df.empty:
st.info("No entries yet. Click the search button in the sidebar.")
else:
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
cutoff = datetime.now() - timedelta(days=days_filter)
view_df = df[df["Date"] >= cutoff].copy()

if outlet_filter:
view_df = view_df[view_df["Outlet"].str.contains(outlet_filter, case=False, na=False)]

view_df = view_df.sort_values(by="Date", ascending=False)

def render_card(row):
st.markdown(f"""
<div class="card">
<div class="card-meta">{row['Formatted_Date']} · {row['Outlet']}</div>
<span class="tag tag-correction">RETRACTION / CORRECTION</span>

<div style="background:#f8fafc; padding:14px; border-radius:8px; margin:12px 0;">
<strong>Correction / Retraction:</strong><br>
{row['Correction']}
</div>

<div style="background:#fee2e2; padding:14px; border-radius:8px; margin:12px 0;">
<strong>Original False Claim / Headline:</strong><br>
{row['Original_Claim']}
</div>

<div class="card-title">
<a href="{row['Link']}" target="_blank">{row['Title']}</a>
</div>
<div class="card-source">Source: {row['Source']}</div>
</div>
""", unsafe_allow_html=True)

col_national, col_state, col_global = st.columns(3)

with col_national:
st.markdown('<h3 class="col-header" style="border-color:#dc2626;">🇺🇸 National</h3>', unsafe_allow_html=True)
for _, row in view_df[view_df["Category"] == "National"].iterrows():
render_card(row)

with col_state:
st.markdown('<h3 class="col-header" style="border-color:#2563eb;">🏛️ State</h3>', unsafe_allow_html=True)
for _, row in view_df[view_df["Category"] == "State"].iterrows():
render_card(row)

with col_global:
st.markdown('<h3 class="col-header" style="border-color:#059669;">🌍 Global</h3>', unsafe_allow_html=True)
for _, row in view_df[view_df["Category"] == "Global/International"].iterrows():
render_card(row)

if view_df.empty:
st.info("No entries match your current filters.")

st.markdown("---")
st.caption(
"Disclaimer: This app collects media self-retractions via NewsAPI and Mediastack. "
"Filtering is strict but not 100% perfect."
)