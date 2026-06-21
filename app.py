import streamlit as st
import pandas as pd
import os
from datetime import datetime
import hashlib
import shutil

CSV_FILE = "political_retractions.csv"
BACKUP_FILE = "political_retractions_backup.csv"

# ==================== Helpers ====================
def generate_id(title, date):
    return hashlib.md5(f"{str(title).strip()}{str(date).strip()}".encode("utf-8")).hexdigest()[:12]

def load_data():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            required = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
                        "Original_Headline", "Original_Claim", "Original_Link",
                        "Correction", "Link", "Source", "Views_Estimate"]
            for col in required:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            pass
    cols = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
            "Original_Headline", "Original_Claim", "Original_Link",
            "Correction", "Link", "Source", "Views_Estimate"]
    df = pd.DataFrame(columns=cols)
    df.to_csv(CSV_FILE, index=False)
    return df

def save_data(df):
    if os.path.exists(CSV_FILE):
        shutil.copy2(CSV_FILE, BACKUP_FILE)
    df.to_csv(CSV_FILE, index=False)

# ==================== APP ====================
st.set_page_config(page_title="Political Retractions Tracker", layout="wide")
st.title("📰 Political Retractions & Corrections Tracker")
st.markdown("**Curated tracker focused on media self-corrections**")

df = load_data()

# ====================== ADD NEW ENTRY ======================
st.header("➕ Add New Retraction / Correction")
with st.form("add_entry"):
    colA, colB = st.columns(2)
    with colA:
        title = st.text_input("Correction Title / Headline *")
        outlet = st.text_input("Outlet *", value="New York Times")
        category = st.selectbox("Category", ["National", "State", "Global/International"])
    with colB:
        correction_link = st.text_input("Link to Correction Article")
        original_link = st.text_input("Link to Original Article (if different)")
        views = st.text_input("Est. Original Views (optional)")

    original_headline = st.text_input("Original Article Headline (optional)")
    original_claim = st.text_area("What the Original Article Claimed", height=100)
    correction = st.text_area("Retraction / Correction Text *", height=180)

    if st.form_submit_button("✅ Add Entry"):
        if title and outlet and correction:
            new_row = pd.DataFrame([{
                "ID": generate_id(title, datetime.now()),
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Formatted_Date": datetime.now().strftime("%b %d, %Y"),
                "Title": title,
                "Outlet": outlet,
                "Category": category,
                "Original_Headline": original_headline,
                "Original_Claim": original_claim or "See linked article",
                "Original_Link": original_link,
                "Correction": correction,
                "Link": correction_link,
                "Source": "Manual",
                "Views_Estimate": views or "N/A"
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success("✅ Entry added successfully!")
            st.rerun()
        else:
            st.error("Title, Outlet, and Correction text are required.")

# ====================== DISPLAY ======================
st.subheader(f"📋 Current Entries ({len(df)})")

if df.empty:
    st.info("No entries yet. Add some above.")
else:
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.sort_values(by="Date", ascending=False)
    
    col1, col2, col3 = st.columns(3)
    
    for col, cat_name, cat_key in zip([col1, col2, col3], 
                                     ["🇺🇸 National", "🏛️ State", "🌍 Global"], 
                                     ["National", "State", "Global/International"]):
        with col:
            st.markdown(f"### {cat_name}")
            for _, row in df[df["Category"] == cat_key].iterrows():
                with st.container(border=True):
                    st.caption(f"**{row['Formatted_Date']}** — {row['Outlet']}")
                    st.markdown(f"**[{row['Title']}]({row.get('Link', '')})**")
                    
                    st.markdown("**🔴 Retraction / Correction**")
                    st.write(row["Correction"])
                    
                    st.markdown("---")  # Clear separator
                    
                    st.markdown("**Original Article**")
                    if row.get("Original_Headline") and str(row["Original_Headline"]).strip() not in ["", "nan"]:
                        st.markdown(f"**{row['Original_Headline']}**")
                    st.write(row["Original_Claim"])
                    
                    if row.get("Original_Link") and str(row["Original_Link"]).strip() not in ["", "nan"]:
                        st.markdown(f"[→ Link to Original Article]({row['Original_Link']})")
                    
                    if row.get("Views_Estimate") and row["Views_Estimate"] != "N/A":
                        st.caption(f"📊 Est. Original Views: {row['Views_Estimate']}")
                    
                    if st.button("🗑️ Delete", key=f"del_{row['ID']}"):
                        df = df[df["ID"] != row["ID"]]
                        save_data(df)
                        st.rerun()

st.markdown("---")
st.caption("**Daily Tip**: Visit [NYT Corrections](https://www.nytimes.com/section/corrections)")