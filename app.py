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
st.markdown("**Strict tracker** — Only clear self-corrections & retractions by the outlet.")

df = load_data()

# ==================== SIDEBAR (Smaller) ====================
with st.sidebar:
    st.header("🔄 Auto Tools")
    if st.button("🌐 Scrape NYT Corrections (Live)", use_container_width=True):
        try:
            from bs4 import BeautifulSoup
            import requests
            url = "https://www.nytimes.com/section/corrections"
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'lxml')
            
            new_entries = []
            for art in soup.find_all('article')[:8]:
                title_tag = art.find(['h3', 'h2'])
                title = title_tag.get_text(strip=True) if title_tag else ""
                link_tag = art.find('a')
                link = "https://www.nytimes.com" + link_tag['href'] if link_tag else ""
                
                if title and any(kw in title.lower() for kw in ["correction", "earlier version", "misstated", "incorrectly"]):
                    new_row = {
                        "ID": generate_id(title, datetime.now()),
                        "Date": datetime.now().strftime("%Y-%m-%d"),
                        "Formatted_Date": datetime.now().strftime("%b %d, %Y"),
                        "Title": title[:150],
                        "Outlet": "New York Times",
                        "Category": "National",
                        "Original_Headline": "See full correction",
                        "Original_Claim": "",
                        "Original_Link": link,
                        "Correction": title,
                        "Link": link,
                        "Source": "NYT Corrections Page"
                    }
                    new_entries.append(new_row)
            
            if new_entries:
                new_df = pd.DataFrame(new_entries)
                df = pd.concat([df, new_df], ignore_index=True).drop_duplicates(subset=["Title", "Outlet"])
                save_data(df)
                st.success(f"✅ Added {len(new_entries)} NYT corrections!")
                st.rerun()
            else:
                st.info("No new corrections found today.")
        except Exception as e:
            st.error(f"Scrape error: {e}")

    if st.button("📊 Load Real Examples", use_container_width=True):
        samples = [
            {"Date": "2026-05-24", "Formatted_Date": "May 24, 2026", "Title": "Florida 20th District Racial Breakdown", "Outlet": "New York Times", "Category": "National", "Original_Headline": "Florida’s 20th District is a majority-Black district", "Original_Claim": "Called it a majority-Black district", "Original_Link": "", "Correction": "It is a majority-minority district, not a majority-Black district. We deleted the earlier post.", "Link": "https://x.com/nytimes/status/2058581220473352276", "Source": "X @nytimes"},
            {"Date": "2026-06-20", "Formatted_Date": "Jun 20, 2026", "Title": "Mets Losing Streak Date Error", "Outlet": "New York Times", "Category": "National", "Original_Headline": "Mets suffered 11th straight loss on wrong day", "Original_Claim": "Wrong date for losing streak", "Original_Link": "", "Correction": "Because of an editing error, an earlier version misstated which day the Mets suffered their 11th straight loss.", "Link": "", "Source": "NYT Correction"},
            {"Date": "2026-02-02", "Formatted_Date": "Feb 02, 2026", "Title": "Bad Bunny Puerto Rico Quote Error", "Outlet": "New York Times", "Category": "National", "Original_Headline": "Quote about Puerto Rico", "Original_Claim": "Incorrectly implied Puerto Rico not part of US", "Original_Link": "", "Correction": "An earlier version included a quote that incorrectly implied Puerto Rico was not part of the United States.", "Link": "", "Source": "X @nytimes"},
        ]
        new_df = pd.DataFrame(samples)
        df = pd.concat([df, new_df], ignore_index=True).drop_duplicates(subset=["Title", "Outlet"])
        save_data(df)
        st.success("✅ Loaded real corrections!")
        st.rerun()

    st.markdown("### Quick Links")
    st.markdown("[NYT Corrections](https://www.nytimes.com/section/corrections)")

# ==================== MAIN CONTENT (Wider) ====================
search_term = st.text_input("🔎 Search all entries (title, outlet, correction...)", "")

st.subheader(f"Current Entries ({len(df)})")

filtered_df = df.copy()
if search_term:
    filtered_df = filtered_df[filtered_df.apply(
        lambda row: search_term.lower() in str(row).lower(), axis=1)]

if filtered_df.empty:
    st.info("No entries yet. Use sidebar buttons to load data.")
else:
    filtered_df = filtered_df.sort_values(by="Date", ascending=False)
    
    # Wider cards using full width
    for _, row in filtered_df.iterrows():
        with st.container(border=True):
            st.caption(f"{row['Formatted_Date']} — {row['Outlet']} | {row.get('Source', 'Manual')}")
            st.markdown(f"**{row['Title']}**")
            
            st.markdown("**Correction:**")
            st.write(row["Correction"])
            
            orig = str(row.get("Original_Headline", "")).strip()
            if orig and orig.lower() not in ["nan", "not provided", ""]:
                st.markdown("**Original Article:**")
                st.write(orig)
            
            col_link1, col_link2 = st.columns([1, 1])
            with col_link1:
                if str(row.get("Link", "")).strip():
                    st.markdown(f"[🔗 View Correction]({row['Link']})")
            with col_link2:
                if str(row.get("Original_Link", "")).strip():
                    st.markdown(f"[🔗 Original Article]({row['Original_Link']})")
            
            # Unique delete key
            if st.button("🗑️ Delete", key=f"del_{row['ID']}"):
                df = df[df["ID"] != row["ID"]]
                save_data(df)
                st.rerun()

# ==================== ADD ENTRY ====================
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
    
    original_claim = st.text_area("Original Claim (summary)", height=60)
    correction_text = st.text_area("Correction Text *", height=100)
    
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
            df = pd.concat([df, new_row], ignore_index=True).drop_duplicates(subset=["Title", "Outlet"])
            save_data(df)
            st.success("✅ Entry added!")
            st.rerun()
        else:
            st.error("Title, Outlet, and Correction text required.")

st.caption("💡 Wider cards + stricter examples. Click sidebar buttons to populate.")