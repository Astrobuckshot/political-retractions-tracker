import streamlit as st
import pandas as pd
import requests
import os
from datetime import datetime, timedelta
import hashlib

# ====================== SECURE API KEY ======================
if "NEWS_API_KEY" not in st.secrets:
    st.error("⚠️ NEWS_API_KEY not found in secrets. Add it in Streamlit Cloud → Settings → Secrets")
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
        try:
            df = pd.read_csv(CSV_FILE)
            required_cols = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
                             "Original_Claim", "Correction", "Link", "Source", "Views_Estimate"]
            for col in required_cols:
                if col not in df.columns:
                    df[col] = "" if col in ["Original_Claim", "Correction", "Source", "Views_Estimate"] else None
            return df
        except Exception as e:
            st.error(f"Error loading CSV: {e}. Creating new file.")
    
    # Create new file
    cols = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
            "Original_Claim", "Correction", "Link", "Source", "Views_Estimate"]
    df = pd.DataFrame(columns=cols)
    df.to_csv(CSV_FILE, index=False)
    return df

def save_data(df):
    df.to_csv(CSV_FILE, index=False)

def categorize_politics(text):
    text = str(text).lower()
    
    national_keywords = {
        "trump", "biden", "harris", "kamala", "vance", "obama", "bush", "clinton", "sanders",
        "warren", "rubio", "cruz", "desantis", "newsom", "pence", "pelosi", "mcconnell",
        "schumer", "congress", "senate", "house", "white house", "potus", "scotus",
        "election", "impeach", "debate", "maga", "democrat", "republican", "gop", "dnc",
        "justice department", "fbi", "cia", "elon musk", "musk", "jeffrey epstein", "epstein",
        "current administration"
    }
    
    state_keywords = {
        "sacramento bee", "san francisco chronicle", "denver post", "chicago tribune",
        "los angeles times", "california", "texas", "new york", "florida", "illinois",
        "governor", "state legislature", "mayor", "ballot measure"
    }
    
    if any(word in text for word in national_keywords):
        return "National"
    elif any(word in text for word in state_keywords):
        return "State"
    return "Global/International"

@st.cache_data(ttl=3600)
def fetch_political_retractions(days_back=14):
    since = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    query = (
        '(retraction OR correction OR erratum OR "we regret" OR clarifies OR "corrected" OR '
        '"retracted" OR "false report" OR "apologizes for") AND '
        '(trump OR biden OR harris OR musk OR epstein OR election OR congress OR scandal OR '
        'administration OR politics OR government OR "false accusation")'
    )
    
    url = f"https://newsapi.org/v2/everything?q={query}&language=en&from={since}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])
        
        new_entries = []
        for art in articles:
            title = art.get("title", "")
            if not title:
                continue
            if not any(kw in title.lower() for kw in ["retract", "correct", "erratum", "regret", "clarif"]):
                continue
                
            cat = categorize_politics(title + " " + art.get("description", ""))
            
            new_entries.append({
                "ID": generate_id(title, art.get("publishedAt")),
                "Date": art.get("publishedAt", "")[:10],
                "Formatted_Date": datetime.strptime(art.get("publishedAt", "")[:10], "%Y-%m-%d").strftime("%b %d, %Y"),
                "Title": title,
                "Outlet": art.get("source", {}).get("name", "Unknown"),
                "Category": cat,
                "Original_Claim": "Original story referenced in the retraction (see full article)",
                "Correction": art.get("description", "Full correction details available at the link."),
                "Link": art.get("url"),
                "Source": "NewsAPI Auto",
                "Views_Estimate": "N/A"
            })
        return pd.DataFrame(new_entries)
    except Exception as e:
        st.error(f"Error fetching from NewsAPI: {e}")
        return pd.DataFrame()

# ==================== MAIN APP ====================
st.set_page_config(page_title="Political Retractions Tracker", layout="wide")
st.title("📰 Automatic Political Retractions & Corrections Tracker")
st.markdown("**Daily catalog of media self-retractions and corrections in political news** • Newest on top")

df = load_data()

# Sidebar
st.sidebar.header("🔄 Automation")
if st.sidebar.button("🔍 Search for New Retractions Now", type="primary"):
    with st.spinner("Searching recent political retractions..."):
        new_df = fetch_political_retractions(days_back=14)
        if not new_df.empty:
            combined = pd.concat([df, new_df]).drop_duplicates(subset=["ID"])
            save_data(combined)
            df = combined
            st.success(f"✅ Added {len(new_df)} new entries!")
            st.rerun()
        else:
            st.info("No new retractions found in the last 14 days.")

st.sidebar.header("Filters")
category_filter = st.sidebar.multiselect(
    "Filter by Category", 
    ["National", "State", "Global/International"], 
    default=["National", "State"]
)

# Main Display
st.subheader("Recent Retractions & Corrections")

if df.empty:
    st.info("No entries yet. Click the search button above to start.")
else:
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.sort_values(by="Date", ascending=False)
    
    filtered_df = df[df["Category"].isin(category_filter)] if category_filter else df
    
    for cat in ["National", "State", "Global/International"]:
        cat_df = filtered_df[filtered_df["Category"] == cat]
        if not cat_df.empty:
            st.markdown(f"### {cat} News")
            for _, row in cat_df.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([1.2, 5])
                    with col1:
                        st.markdown(f"**{row['Formatted_Date']}**")
                    with col2:
                        st.markdown(f"**{row['Outlet']}** • [{row['Title']}]({row['Link']})")
                    
                    st.markdown("**🔴 Retraction / Correction**")
                    st.write(row["Correction"])
                    
                    st.markdown("**Original Story**")
                    st.write(row["Original_Claim"])
                    
                    if row.get("Views_Estimate") and row["Views_Estimate"] != "N/A":
                        st.caption(f"📊 Est. Original Views: {row['Views_Estimate']}")
                    
                    st.caption(f"Source: {row['Source']} | ID: {row['ID']}")

# Disclaimer
st.markdown("---")
st.caption("""
**Disclaimer**: This app automatically collects publicly reported self-retractions, corrections, and errata 
from news outlets. It is **not** a fact-checking service. It only tracks what the media outlets themselves 
publish as corrections or retractions. Always read the original articles for full context.
""")

# Manual Entry
with st.expander("➕ Manual Entry"):
    with st.form("manual_entry"):
        title = st.text_input("Retraction Title*")
        outlet = st.text_input("Outlet*")
        cat = st.selectbox("Category", ["National", "State", "Global/International"])
        original = st.text_area("Original Claim Summary")
        correction = st.text_area("Correction / Retraction Text*")
        link = st.text_input("Link to Article")
        
        if st.form_submit_button("Add Retraction"):
            if title and outlet and correction:
                new_row = pd.DataFrame([{
                    "ID": generate_id(title, datetime.now().date()),
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Formatted_Date": datetime.now().strftime("%b %d, %Y"),
                    "Title": title,
                    "Outlet": outlet,
                    "Category": cat,
                    "Original_Claim": original or "See linked article",
                    "Correction": correction,
                    "Link": link,
                    "Source": "Manual",
                    "Views_Estimate": "N/A"
                }])
                df = pd.concat([df, new_row], ignore_index=True)
                save_data(df)
                st.success("Entry added successfully!")
                st.rerun()