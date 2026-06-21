import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
import hashlib

# ====================== SECURE API KEY ======================
if "NEWS_API_KEY" not in st.secrets:
    st.error("⚠️ NEWS_API_KEY not found in secrets.")
    st.stop()

NEWS_API_KEY = st.secrets["NEWS_API_KEY"]

CSV_FILE = "political_retractions.csv"

# ==================== Helpers ====================
def generate_id(title, date):
    clean_title = str(title).strip()
    clean_date = str(date).strip()
    return hashlib.md5(f"{clean_title}{clean_date}".encode("utf-8")).hexdigest()[:12]

def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        required = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
                    "Original_Claim", "Correction", "Link", "Source", "Views_Estimate"]
        for col in required:
            if col not in df.columns:
                df[col] = "" if col in ["Original_Claim", "Correction", "Source", "Views_Estimate"] else None
        return df
    cols = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
            "Original_Claim", "Correction", "Link", "Source", "Views_Estimate"]
    df = pd.DataFrame(columns=cols)
    df.to_csv(CSV_FILE, index=False)
    return df

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

def categorize_politics(text):
    text = str(text).lower()
    national = {"trump", "biden", "harris", "musk", "epstein", "congress", "election", "white house", "potus", "administration", "newsom"}
    state = {"sacramento", "san francisco", "denver", "chicago", "california", "texas", "new york", "florida", "governor"}
    if any(k in text for k in national):
        return "National"
    elif any(k in text for k in state):
        return "State"
    return "Global/International"

@st.cache_data(ttl=3600)
def fetch_political_retractions(days_back=14):
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    # Extremely strict - looking for self-corrections by media outlets
    query = (
        '("Correction:" OR "Retraction:" OR "Clarification:" OR "A correction" OR "This article was corrected" OR '
        '"We regret" OR "Corrects:" OR "editor\'s note" OR "in our story" OR "earlier version") AND '
        '(trump OR biden OR harris OR musk OR epstein OR election OR congress OR administration)'
    )
    
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&from={since}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        
        new_entries = []
        for art in articles:
            title = art.get("title") or ""
            desc = art.get("description") or ""
            if not title:
                continue
                
            full_text = (title + " " + desc).lower()
            
            # Must have strong correction signal in title
            correction_words = ["correction", "retraction", "clarification", "corrects", "we regret", "editor's note"]
            if not any(word in title.lower() for word in correction_words):
                continue
            
            # Block false positives aggressively
            bad_phrases = [
                "whoopi", "goldberg", "clarifies", "talking about", "discusses", "regarding", 
                "interview", "has various", "stances on", "german ambassador", "rfk"
            ]
            if any(phrase in full_text for phrase in bad_phrases):
                continue
            
            cat = categorize_politics(full_text)
            
            new_entries.append({
                "ID": generate_id(title, art.get("publishedAt")),
                "Date": art.get("publishedAt", "")[:10],
                "Formatted_Date": datetime.strptime(art.get("publishedAt", "")[:10], "%Y-%m-%d").strftime("%b %d, %Y"),
                "Title": title,
                "Outlet": art.get("source", {}).get("name", "Unknown"),
                "Category": cat,
                "Original_Claim": "Original story referenced in this correction (see full article)",
                "Correction": desc or "Full correction details at the link.",
                "Link": art.get("url"),
                "Source": "NewsAPI Auto",
                "Views_Estimate": "N/A"
            })
        return pd.DataFrame(new_entries)
    except Exception as e:
        st.error(f"Error fetching: {e}")
        return pd.DataFrame()

# ==================== APP ====================
st.set_page_config(page_title="Political Retractions Tracker", layout="wide")
st.title("📰 Automatic Political Retractions & Corrections Tracker")
st.markdown("**Daily catalog of media self-retractions & corrections in political news** • Newest on top")

df = load_data()

st.sidebar.header("🔄 Automation")
if st.sidebar.button("🔍 Search for New Retractions Now", type="primary"):
    with st.spinner("Searching very strictly for media self-corrections..."):
        new_df = fetch_political_retractions(days_back=14)
        if not new_df.empty:
            combined = pd.concat([df, new_df]).drop_duplicates(subset=["ID"])
            save_data(combined)
            st.success(f"✅ Added {len(new_df)} new entries!")
            st.rerun()
        else:
            st.info("No qualifying self-corrections found in the last 14 days.")

# Display (3 columns)
st.subheader("Recent Retractions & Corrections")

if df.empty:
    st.info("No entries yet. Click the search button above.")
else:
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.sort_values(by="Date", ascending=False)
    
    col1, col2, col3 = st.columns(3)
    
    for col, cat_name, cat_key in zip([col1, col2, col3], 
                                     ["🇺🇸 National", "🏛️ State", "🌍 Global"], 
                                     ["National", "State", "Global/International"]):
        with col:
            st.markdown(f"### {cat_name}")
            cat_df = df[df["Category"] == cat_key]
            for _, row in cat_df.iterrows():
                with st.container(border=True):
                    st.caption(f"**{row['Formatted_Date']}** — {row['Outlet']}")
                    st.markdown(f"**[{row['Title']}]({row['Link']})**")
                    st.markdown("**🔴 Retraction / Correction**")
                    st.write(row["Correction"])
                    st.markdown("**Original Story**")
                    st.write(row["Original_Claim"])
                    st.caption(f"Source: {row['Source']}")

st.markdown("---")
st.caption("**Disclaimer**: This app collects self-retractions published by media outlets. It is not a fact-checking service.")