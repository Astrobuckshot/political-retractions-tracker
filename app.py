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
                        "Original_Claim", "Correction", "Link", "Source", "Views_Estimate"]
            for col in required:
                if col not in df.columns:
                    df[col] = ""
            return df
        except:
            pass
    # Create new
    cols = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
            "Original_Claim", "Correction", "Link", "Source", "Views_Estimate"]
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
st.markdown("**Curated tracker** • Manual entry recommended • Delete bad entries easily")

df = load_data()

# ====================== ADD NEW ENTRY ======================
st.header("➕ Add New Retraction / Correction")
with st.form("add_entry"):
    colA, colB = st.columns(2)
    with colA:
        title = st.text_input("Title of Correction Article *")
        outlet = st.text_input("News Outlet *")
        category = st.selectbox("Category", ["National", "State", "Global/International"])
    with colB:
        link = st.text_input("Link to the Article")
        views = st.text_input("Est. Original Views (optional)")

    original = st.text_area("Original Claim / Story Summary", height=100)
    correction = st.text_area("Retraction / Correction Text *", height=150)

    if st.form_submit_button("✅ Add Entry"):
        if title and outlet and correction:
            new_row = pd.DataFrame([{
                "ID": generate_id(title, datetime.now()),
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Formatted_Date": datetime.now().strftime("%b %d, %Y"),
                "Title": title,
                "Outlet": outlet,
                "Category": category,
                "Original_Claim": original or "See linked article",
                "Correction": correction,
                "Link": link,
                "Source": "Manual",
                "Views_Estimate": views or "N/A"
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success("✅ Entry added!")
            st.rerun()
        else:
            st.error("Title, Outlet, and Correction text are required.")

# ====================== DISPLAY WITH DELETE BUTTONS ======================
st.subheader(f"📋 Current Entries ({len(df)})")

if df.empty:
    st.info("No entries yet.")
else:
    df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
    df = df.sort_values(by="Date", ascending=False)
    
    col1, col2, col3 = st.columns(3)
    
    for col, cat_name, cat_key in zip([col1, col2, col3], 
                                     ["🇺🇸 National", "🏛️ State", "🌍 Global"], 
                                     ["National", "State", "Global/International"]):
        with col:
            st.markdown(f"### {cat_name}")
            cat_df = df[df["Category"] == cat_key].copy()
            
            for idx, row in cat_df.iterrows():
                with st.container(border=True):
                    st.caption(f"**{row['Formatted_Date']}** — {row['Outlet']}")
                    st.markdown(f"**[{row['Title']}]({row.get('Link', '')})**")
                    
                    st.markdown("**🔴 Retraction / Correction**")
                    st.write(row["Correction"])
                    
                    st.markdown("**Original Story**")
                    st.write(row["Original_Claim"])
                    
                    if row.get("Views_Estimate") and row["Views_Estimate"] != "N/A":
                        st.caption(f"📊 Est. Views: {row['Views_Estimate']}")
                    
                    st.caption(f"Source: {row['Source']}")
                    
                    # Delete button for each entry
                    if st.button("🗑️ Delete This Entry", key=f"del_{row['ID']}"):
                        df = df[df["ID"] != row["ID"]]
                        save_data(df)
                        st.success("Entry deleted.")
                        st.rerun()

st.markdown("---")
st.caption("**Tip**: Use the Delete buttons to remove bad automated entries (Whoopi, RFK, etc.)")
