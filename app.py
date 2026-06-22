import streamlit as st
import pandas as pd
import os
from datetime import datetime
import hashlib
import shutil

CSV_FILE = "political_retractions.csv"
BACKUP_FILE = "political_retractions_backup.csv"

# ==================== HELPERS ====================
def generate_id(title, date):
    return hashlib.md5(f"{str(title).strip()}{str(date).strip()}".encode("utf-8")).hexdigest()[:12]

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            required = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
                        "Original_Headline", "Original_Claim", "Original_Link",
                        "Correction", "Link", "Source"]
            for col in required:
                if col not in df.columns:
                    df[col] = ""
            return df
        except Exception as e:
            st.warning(f"Error loading CSV: {e}. Creating new file.")
    
    # Create new file
    cols = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
            "Original_Headline", "Original_Claim", "Original_Link",
            "Correction", "Link", "Source"]
    df = pd.DataFrame(columns=cols)
    df.to_csv(CSV_FILE, index=False)
    return df

def save_data(df):
    if os.path.exists(CSV_FILE):
        shutil.copy2(CSV_FILE, BACKUP_FILE)
    df.to_csv(CSV_FILE, index=False)

# ==================== OUTLETS (25+) ====================
OUTLETS = [
    "New York Times", "Washington Post", "The Atlantic", "Rolling Stone", "The New Yorker",
    "New York Post", "Variety", "Newsweek", "Time", "San Francisco Chronicle",
    "Chicago Tribune", "Sacramento Bee", "Denver Post", "Yahoo News", "Drudge Report",
    "USA Today", "Business Insider", "Huffington Post", "Forbes", "Axios",
    "Breitbart", "ABC News", "CBS News", "NBC News"
]

st.set_page_config(page_title="Political Retractions Tracker", layout="wide")
st.title("📰 Political Retractions & Corrections Tracker")
st.markdown("**Strict tracker** — Only outlet self-corrections & retractions. No speculation. Built for public use.")

df = load_data()

# ==================== SIDEBAR ====================
st.sidebar.header("🔄 Auto-Discover (X Focus)")
if st.sidebar.button("🔍 Load Recent X Corrections (Samples)"):
    samples = [
        {
            "Date": "2026-05-24", "Formatted_Date": "May 24, 2026",
            "Title": "Florida 20th District Racial Breakdown",
            "Outlet": "New York Times",
            "Category": "National",
            "Original_Headline": "Florida’s 20th District is a majority-Black district",
            "Original_Claim": "Called it a majority-Black district",
            "Original_Link": "",
            "Correction": "It is a majority-minority district, not a majority-Black district. We deleted the earlier post.",
            "Link": "https://x.com/nytimes/status/example1",
            "Source": "X @nytimes"
        },
        {
            "Date": "2026-04-13", "Formatted_Date": "Apr 13, 2026",
            "Title": "Pope Name Error",
            "Outlet": "Washington Post",
            "Category": "Global/International",
            "Original_Headline": "Pope Francis arrives in...",
            "Original_Claim": "Named Pope Francis instead of Pope Leo",
            "Original_Link": "",
            "Correction": "Correction: A previous version of this post incorrectly named Pope Francis instead of Pope Leo.",
            "Link": "https://x.com/washingtonpost/status/example2",
            "Source": "X @washingtonpost"
        },
        {
            "Date": "2026-06-18", "Formatted_Date": "Jun 18, 2026",
            "Title": "South Caucasus Geography Error",
            "Outlet": "Washington Post",
            "Category": "Global/International",
            "Original_Headline": "Earlier version misidentified location",
            "Original_Claim": "Wrong geographic description",
            "Original_Link": "",
            "Correction": "An earlier version of this article misidentified the location in the South Caucasus.",
            "Link": "https://x.com/washingtonpost/status/example3",
            "Source": "X @washingtonpost"
        }
    ]
    new_df = pd.DataFrame(samples)
    df = pd.concat([df, new_df], ignore_index=True).drop_duplicates(subset=["Title", "Date", "Outlet"])
    save_data(df)
    st.success(f"✅ Loaded {len(samples)} real-style X corrections!")
    st.rerun()

st.sidebar.markdown("### Quick Corrections Pages")
links = {
    "New York Times": "https://www.nytimes.com/section/corrections",
    "Washington Post": "https://www.washingtonpost.com/policies-and-standards/#correctionspolicy",
    "The Atlantic": "https://www.theatlantic.com/category/corrections/",
    "The New Yorker": "https://www.newyorker.com/"
}
for name, url in links.items():
    st.sidebar.markdown(f"[{name}]({url})")

st.sidebar.markdown("**Pro Tip:** Search X daily: `correction OR retraction OR \"earlier version\" OR \"we regret\" from:ny