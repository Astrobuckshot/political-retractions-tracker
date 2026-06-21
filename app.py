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
st.markdown("**Curated tracker focused on major outlets like NYT Corrections**")

df = load_data()

# Quick Links
st.sidebar.markdown("### Useful Links")
st.sidebar.markdown("[NYT Corrections](https://www.nytimes.com/section/corrections)")
st.sidebar.markdown("[WaPo Corrections](https://www.washingtonpost.com/newsroom/corrections/)")
st.sidebar.markdown("[CNN Corrections](https://www.cnn.com/corrections)")

# ====================== MANUAL ENTRY ======================
st.header("➕ Add New Retraction / Correction (from NYT, etc.)")
with st.form("add_entry"):
    colA, colB = st.columns(2)
    with colA:
        title = st.text_input("Correction Title / Headline *")
        outlet = st.text_input("Outlet *", value="New York Times")
        category = st.selectbox("Category", ["National", "State", "Global/International"])
    with colB:
        link = st.text_input("Direct Link to Correction")
        views = st.text_input("Est. Original Views (optional)")

    original = st.text_area("What the Original Article Said (problematic claim)", height=120)
    correction = st.text_area("The Correction / Retraction Text *", height=180)

    if st.form_submit_button("✅ Add to Tracker"):
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
                "Source": "Manual (NYT Corrections etc.)",
                "Views_Estimate": views or "N/A"
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success("✅ Entry added successfully!")
            st.rerun()
        else:
            st.error("Title, Outlet, and Correction text are required.")

# Display
st.subheader(f"📋 Current Entries ({len(df)})")

if df.empty:
    st.info("No entries yet. Start adding from NYT Corrections page.")
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
                    st.markdown("**Original Story**")
                    st.write(row["Original_Claim"])
                    if row.get("Views_Estimate") and row["Views_Estimate"] != "N/A":
                        st.caption(f"📊 Est. Views: {row['Views_Estimate']}")
                    if st.button("🗑️ Delete", key=f"del_{row['ID']}"):
                        df = df[df["ID"] != row["ID"]]
                        save_data(df)
                        st.rerun()

st.markdown("---")
st.caption("**Daily Routine Tip**: Visit https://www.nytimes.com/section/corrections every day and add relevant political ones here.")