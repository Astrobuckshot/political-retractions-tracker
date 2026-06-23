import streamlit as st
import pandas as pd
import os
from datetime import datetime
import hashlib
import shutil
from bs4 import BeautifulSoup
import requests

CSV_FILE = "political_retractions.csv"
BACKUP_FILE = "political_retractions_backup.csv"

def generate_id(title, date):
    return hashlib.md5(f"{str(title).strip()}{str(date).strip()}".encode("utf-8")).hexdigest()[:12]

def clean_text(text):
    if not isinstance(text, str):
        return str(text) if text is not None else ""
    replacements = {"â€™": "'", "’": "'", "â€œ": '"', "â€": '"', "â€“": "–", "â€”": "—", "Â": ""}
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            required = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
                        "Original_Headline", "Original_Claim", "Original_Link",
                        "Correction", "Link", "Source", "Retraction_Target"]
            for col in required:
                if col not in df.columns:
                    df[col] = ""
            for col in ["Title", "Correction", "Original_Headline", "Original_Claim"]:
                df[col] = df[col].apply(clean_text)
            return df
        except:
            pass
    df = pd.DataFrame(columns=["ID","Date","Formatted_Date","Title","Outlet","Category",
                               "Original_Headline","Original_Claim","Original_Link",
                               "Correction","Link","Source","Retraction_Target"])
    df.to_csv(CSV_FILE, index=False)
    return df

def save_data(df):
    if os.path.exists(CSV_FILE):
        shutil.copy2(CSV_FILE, BACKUP_FILE)
    df.to_csv(CSV_FILE, index=False)

OUTLETS = ["New York Times", "Washington Post", "Wall Street Journal", "NBC News", "ABC News",
           "CBS News", "CNN", "FOX News", "The Hill", "Politico", "AP", "Reuters", "Time",
           "Newsweek", "Rolling Stone", "The Atlantic", "New York Post", "Sacramento Bee",
           "Chicago Tribune", "Denver Post", "L.A. Times", "San Francisco Chronicle",
           "USA Today", "Breitbart", "Huffington Post", "Mother Jones", "Salon", "Axios", 
           "Daily Beast", "The National Review", "Jezebel", "Media Matters", "PBS", "NPR"]

st.set_page_config(page_title="Political Retractions Tracker", layout="wide")

st.markdown("""<style>
    .main .block-container {padding-top: 1rem;}
    .retraction-card {
        background: #1e1e1e;
        border: 1px solid #333;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 20px;
    }
    .retraction-bar {
        background: #006400;
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 12px 0;
        font-weight: 500;
    }
    .original-bar {
        background: #8B0000;
        color: white;
        padding: 12px 16px;
        border-radius: 8px;
        margin: 12px 0;
        font-weight: 500;
    }
</style>""", unsafe_allow_html=True)

st.title("📰 Political Retractions & Corrections Tracker")
st.markdown("**Strict tracker** — ONLY media outlets correcting their own stories")

df = load_data()

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("🔄 Tools")

    if st.button("🌐 Scrape CAMERA.org Corrections (Best Source)", use_container_width=True):
        with st.spinner("Scraping CAMERA.org for documented corrections..."):
            try:
                new_entries = []
                outlet_slugs = ["new-york-times", "washington-post", "politico", "cbs", "abc", "cnn", "pbs", "npr"]
                for slug in outlet_slugs:
                    url = f"https://www.camera.org/article/topic/media-corrections/outlet/{slug}"
                    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    response = requests.get(url, headers=headers, timeout=15)
                    soup = BeautifulSoup(response.text, 'lxml')
                    
                    for item in soup.find_all('h2')[:8]:
                        title = item.get_text(strip=True)
                        link_tag = item.find('a')
                        link = link_tag['href'] if link_tag and link_tag.has_attr('href') else url
                        if title and any(k in title.lower() for k in ["correction", "corrects", "retract", "error", "misstated", "amends", "deleted"]):
                            outlet_name = slug.replace('-', ' ').title().replace("Npr", "NPR").replace("Pbs", "PBS")
                            new_entries.append({
                                "ID": generate_id(title, datetime.now()), 
                                "Date": datetime.now().strftime("%Y-%m-%d"),
                                "Formatted_Date": datetime.now().strftime("%b %d, %Y"), 
                                "Title": title[:160],
                                "Outlet": outlet_name, 
                                "Category": "National", 
                                "Original_Headline": "See CAMERA report",
                                "Original_Claim": "",
                                "Correction": f"CAMERA-documented: {title}",
                                "Link": link if link.startswith("http") else f"https://www.camera.org{link}",
                                "Source": "CAMERA.org",
                                "Retraction_Target": outlet_name
                            })
                if new_entries:
                    new_df = pd.DataFrame(new_entries)
                    for col in ["Title", "Correction"]:
                        new_df[col] = new_df[col].apply(clean_text)
                    df = pd.concat([df, new_df], ignore_index=True).drop_duplicates(subset=["Title", "Outlet", "Source"])
                    save_data(df)
                    st.success(f"✅ Added {len(new_entries)} strong corrections from CAMERA.org!")
                    st.rerun()
                else:
                    st.warning("No new entries found — try again or check the site directly.")
            except Exception as e:
                st.error(f"CAMERA scrape error: {str(e)[:100]}")

    if st.button("🌐 White House Media Offenders (Secondary)", use_container_width=True):
        with st.spinner("Checking White House page..."):
            try:
                url = "https://www.whitehouse.gov/mediabias/"
                soup = BeautifulSoup(requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10).text, 'lxml')
                # (simplified parser - add more if needed)
                st.info("White House page loaded — manual review recommended for best results.")
            except Exception as e:
                st.error(f"White House error: {e}")

    if st.button("🧹 Clean False Positives + Fix Text", use_container_width=True):
        bad_keywords = ["COVID", "Covid", "coronavirus", "vaccine", "clinical trial", "Dr. Sabine", "Kyle Cooke", "Summer House", "RFK Jr"]
        df = df[~df.apply(lambda row: any(kw.lower() in str(row).lower() for kw in bad_keywords), axis=1)]
        for col in ["Title", "Correction", "Original_Headline", "Original_Claim"]:
            df[col] = df[col].apply(clean_text)
        save_data(df)
        st.success("🧼 Cleaned!")
        st.rerun()

# ====================== MAIN DISPLAY ======================
search_term = st.text_input("🔎 Search entries", "")

st.subheader(f"Current Entries ({len(df)})")

filtered_df = df.copy()
if search_term:
    filtered_df = filtered_df[filtered_df.apply(lambda r: search_term.lower() in str(r).lower(), axis=1)]

filtered_df = filtered_df.sort_values(by="Date", ascending=False)

for idx, row in filtered_df.iterrows():
    with st.container():
        st.markdown(f"""
        <div class="retraction-card">
            <small>{row['Formatted_Date']} — {row['Outlet']} | {row.get('Source','')}</small>
        """, unsafe_allow_html=True)
        
        if row.get("Retraction_Target"):
            st.caption(f"**Retraction Target:** {row['Retraction_Target']}")
        
        st.markdown(f"**{row['Title']}**")
        
        st.markdown(f"""
            <div class="retraction-bar">
                ✅ Retraction / Correction:<br>
                {row['Correction']}
            </div>
        """, unsafe_allow_html=True)
        
        orig_text = row.get("Original_Headline") or row.get("Original_Claim") or "No original details provided"
        st.markdown(f"""
            <div class="original-bar">
                ❌ Original Headline / Claim:<br>
                {orig_text}
            </div>
        """, unsafe_allow_html=True)
        
        if row.get("Link"):
            st.markdown(f"[🔗 View]({row['Link']})")
        
        if st.button("🗑️ Delete Entry", key=f"del_{row['ID']}_{idx}"):
            df = df[df["ID"] != row["ID"]]
            save_data(df)
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)

# Manual Add (same)
st.header("➕ Add New Entry (Manual)")
with st.form("add_entry"):
    c1, c2 = st.columns(2)
    with c1:
        title = st.text_input("Title *")
        outlet = st.selectbox("Outlet (who retracted)", OUTLETS)
        category = st.selectbox("Category", ["National", "State", "Global/International"])
        retraction_target = st.text_input("Retraction Target (if 3rd party)")
    with c2:
        link = st.text_input("Correction Link")
        orig_head = st.text_input("Original Headline")
        claim = st.text_area("Original Claim", height=60)
        correction = st.text_area("Correction / Retraction Text *", height=100)
        source = st.text_input("Source", value="Manual")

    if st.form_submit_button("Add Entry"):
        if title and outlet and correction:
            new_row = pd.DataFrame([{
                "ID": generate_id(title, datetime.now()), "Date": datetime.now().strftime("%Y-%m-%d"),
                "Formatted_Date": datetime.now().strftime("%b %d, %Y"), "Title": clean_text(title.strip()[:150]),
                "Outlet": outlet, "Category": category, "Original_Headline": clean_text(orig_head or ""),
                "Original_Claim": clean_text(claim), "Original_Link": "", "Correction": clean_text(correction.strip()),
                "Link": link, "Source": source, "Retraction_Target": retraction_target
            }])
            df = pd.concat([df, new_row], ignore_index=True).drop_duplicates(subset=["Title", "Outlet", "Source"])
            save_data(df)
            st.success("✅ Added!")
            st.rerun()

st.caption("Fixed CAMERA.org scraper • PBS & NPR included • Click the CAMERA button for real results!")