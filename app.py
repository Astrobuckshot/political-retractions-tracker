import streamlit as st
import pandas as pd
import os
from datetime import datetime
import hashlib
import shutil
import requests
from bs4 import BeautifulSoup  # pip install beautifulsoup4 lxml

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
        except:
            pass
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

# ==================== OUTLETS ====================
OUTLETS = ["New York Times", "Washington Post", "The Atlantic", "Rolling Stone", "The New Yorker",
           "New York Post", "Variety", "Newsweek", "Time", "San Francisco Chronicle",
           "Chicago Tribune", "Sacramento Bee", "Denver Post", "Yahoo News", "Drudge Report",
           "USA Today", "Business Insider", "Huffington Post", "Forbes", "Axios",
           "Breitbart", "ABC News", "CBS News", "NBC News"]

st.set_page_config(page_title="Political Retractions Tracker", layout="wide")
st.title("📰 Political Retractions & Corrections Tracker")
st.markdown("**Strict tracker** — Only clear self-corrections/retractions by the outlet itself.")

df = load_data()

# ==================== SIDEBAR + AUTO SCRAPE ====================
st.sidebar.header("🔄 Auto Scrape Corrections")

if st.sidebar.button("🌐 Scrape NYT Corrections (Live)"):
    try:
        url = "https://www.nytimes.com/section/corrections"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'lxml')
        
        new_entries = []
        articles = soup.find_all('article')[:5]  # Limit to recent
        
        for art in articles:
            title_tag = art.find('h3') or art.find('h2')
            title = title_tag.get_text(strip=True) if title_tag else "NYT Correction"
            link = "https://www.nytimes.com" + art.find('a')['href'] if art.find('a') else ""
            
            # Strict filter - only include if it looks like a real correction
            if any(word in title.lower() for word in ["correction", "corrections", "earlier version", "misstated", "incorrectly"]):
                new_row = {
                    "ID": generate_id(title, datetime.now()),
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Formatted_Date": datetime.now().strftime("%b %d, %Y"),
                    "Title": title,
                    "Outlet": "New York Times",
                    "Category": "National",
                    "Original_Headline": "See linked correction",
                    "Original_Claim": "",
                    "Original_Link": link,
                    "Correction": f"Full correction details at {link}",
                    "Link": link,
                    "Source": "NYT Corrections Page"
                }
                new_entries.append(new_row)
        
        if new_entries:
            new_df = pd.DataFrame(new_entries)
            df = pd.concat([df, new_df], ignore_index=True).drop_duplicates(subset=["Title", "Date", "Outlet"])
            save_data(df)
            st.success(f"✅ Added {len(new_entries)} new NYT corrections!")
            st.rerun()
        else:
            st.info("No new clear corrections found today.")
    except Exception as e:
        st.error(f"Scrape failed: {e}")

if st.sidebar.button("🐦 Load Real X Corrections"):
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
            "Link": "https://x.com/nytimes/status/2058581220473352276",
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
            "Link": "https://x.com/washingtonpost/status/2043717984892416053",
            "Source": "X @washingtonpost"
        }
    ]
    new_df = pd.DataFrame(samples)
    df = pd.concat([df, new_df], ignore_index=True).drop_duplicates(subset=["Title", "Date", "Outlet"])
    save_data(df)
    st.success("✅ Loaded real X corrections!")
    st.rerun()

# Quick links
st.sidebar.markdown("### Corrections Pages")
st.sidebar.markdown("[NYT Corrections](https://www.nytimes.com/section/corrections)")
st.sidebar.markdown("[WaPo Standards](https://www.washingtonpost.com/policies-and-standards/#correctionspolicy)")

# ==================== SEARCH & DISPLAY (unchanged but improved) ====================
search_term = st.text_input("🔎 Search entries", "")

st.subheader(f"Current Entries ({len(df)})")

filtered_df = df.copy()
if search_term:
    filtered_df = filtered_df[filtered_df.apply(lambda row: search_term.lower() in str(row).lower(), axis=1)]

if filtered_df.empty:
    st.info("No matching entries.")
else:
    filtered_df = filtered_df.sort_values(by="Date", ascending=False)
    col1, col2, col3 = st.columns(3)
    for col, cat_name, cat_key in zip([col1, col2, col3], ["National", "State", "Global"], ["National", "State", "Global/International"]):
        with col:
            st.markdown(f"### {cat_name}")
            cat_df = filtered_df[filtered_df["Category"] == cat_key]
            for _, row in cat_df.iterrows():
                with st.container(border=True):
                    st.caption(f"{row['Formatted_Date']} — {row['Outlet']} | {row.get('Source', 'Manual')}")
                    st.markdown(f"**{row['Title']}**")
                    st.markdown("**Correction:**")
                    st.write(row["Correction"])
                    if str(row.get("Original_Claim", "")).strip():
                        st.markdown("**Original Claim:**")
                        st.write(row["Original_Claim"])
                    
                    orig_head = str(row.get("Original_Headline", "")).strip()
                    if orig_head and orig_head.lower() not in ["nan", "not provided", ""]:
                        st.markdown("**Original Article:**")
                        st.write(orig_head)
                    
                    if str(row.get("Link", "")).strip():
                        st.markdown(f"[🔗 View Correction]({row['Link']})")
                    if str(row.get("Original_Link", "")).strip():
                        st.markdown(f"[🔗 Original]({row['Original_Link']})")
                    
                    if st.button("🗑️ Delete", key=f"del_{row['ID']}"):
                        df = df[df["ID"] != row["ID"]]
                        save_data(df)
                        st.rerun()

# Add form remains the same...
st.header("➕ Add New Retraction / Correction")
with st.form("add_entry"):
    colA, colB = st.columns(2)
    with colA:
        title = st.text_input("Title / Headline of Correction *")
        outlet = st.selectbox("Outlet *", OUTLETS)
        category = st.selectbox("Category", ["National", "State", "Global/International"])
    with colB:
        correction_link = st.text_input("Link to Correction")
        original_link = st.text_input("Link to Original Article")
        original_headline = st.text_input("Original Headline")
    original_claim = st.text_area("Original Claim Summary", height=80)
    correction_text = st.text_area("Correction Text *", height=120)
    
    if st.form_submit_button("Add Entry"):
        if title and outlet and correction_text:
            new_row = pd.DataFrame([{
                "ID": generate_id(title, datetime.now()),
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Formatted_Date": datetime.now().strftime("%b %d, %Y"),
                "Title": title.strip(),
                "Outlet": outlet,
                "Category": category,
                "Original_Headline": original_headline.strip() or "Not provided",
                "Original_Claim": original_claim.strip(),
                "Original_Link": original_link.strip(),
                "Correction": correction_text.strip(),
                "Link": correction_link.strip(),
                "Source": "Manual"
            }])
            df = pd.concat([df, new_row], ignore_index=True).drop_duplicates(subset=["Title", "Date", "Outlet"])
            save_data(df)
            st.success("✅ Added!")
            st.rerun()
        else:
            st.error("Required fields missing.")

st.caption("Use the sidebar buttons daily. Strict filters = quality data.")