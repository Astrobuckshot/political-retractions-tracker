import streamlit as st
import pandas as pd
import os
from datetime import datetime
import hashlib

CSV_FILE = "political_retractions.csv"

# ==================== Helpers ====================
def generate_id(title, date):
    return hashlib.md5(f"{str(title).strip()}{str(date).strip()}".encode("utf-8")).hexdigest()[:12]

def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        required = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
                    "Original_Claim", "Correction", "Link", "Source", "Views_Estimate"]
        for col in required:
            if col not in df.columns:
                df[col] = ""
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
    if any(k in text for k in ["trump", "biden", "harris", "musk", "epstein", "congress", "election", "white house", "kirk"]):
        return "National"
    elif any(k in text for k in ["sacramento", "san francisco", "denver", "chicago", "california", "texas", "governor"]):
        return "State"
    return "Global/International"

# ==================== APP ====================
st.set_page_config(page_title="Political Retractions Tracker", layout="wide")
st.title("📰 Political Retractions & Corrections Tracker")
st.markdown("**High-quality catalog of media self-corrections** • Focused on major outlets like NYT Corrections")

df = load_data()

# ====================== ADD NEW ENTRY (Prominent) ======================
st.header("➕ Add New Retraction / Correction")
with st.form("add_entry"):
    colA, colB = st.columns(2)
    with colA:
        title = st.text_input("Title of the Correction Article *")
        outlet = st.text_input("Outlet * (e.g. New York Times)")
        category = st.selectbox("Category", ["National", "State", "Global/International"])
    with colB:
        link = st.text_input("Link to the Correction")
        views = st.text_input("Estimated Original Views (optional)")

    original = st.text_area("Original False/Problematic Claim", height=120)
    correction = st.text_area("Retraction / Correction Text *", height=150)

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
                "Source": "Manual Entry",
                "Views_Estimate": views or "N/A"
            }])
            df = pd.concat([df, new_row], ignore_index=True)
            save_data(df)
            st.success("✅ Entry successfully added!")
            st.rerun()
        else:
            st.error("Title, Outlet, and Correction text are required.")

# Display
st.subheader("📋 Current Database")

if df.empty:
    st.info("No entries yet. Add your first one using the form above.")
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
                    if row.get("Views_Estimate") != "N/A":
                        st.caption(f"📊 Est. Views: {row['Views_Estimate']}")
                    st.caption(f"Source: {row['Source']}")

st.markdown("---")
st.caption("**Tip**: Check NYT Corrections daily → https://www.nytimes.com/section/corrections  \n"
           "**Disclaimer**: This is a curated tracker of media self-corrections. Not a fact-checking service.")
