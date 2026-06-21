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
    return hashlib.md5(f"{str(title).strip()}{str(date).strip()}".encode("utf-8")).hexdigest()[:12]

def load_data():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        required_cols = ["ID", "Date", "Formatted_Date", "Title", "Outlet", "Category",
                        "Original_Claim", "Correction", "Link", "Source", "Views_Estimate"]
        for col in required_cols:
            if col not in df.columns:
                df[col] = ""
        return df
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
    if any(k in text for k in ["trump", "biden", "harris", "musk", "epstein", "congress", "election", "white house"]):
        return "National"
    elif any(k in text for k in ["sacramento", "san francisco", "denver", "chicago", "california", "texas", "governor"]):
        return "State"
    return "Global/International"

# ==================== MAIN APP ====================
st.set_page_config(page_title="Political Retractions Tracker", layout="wide")
st.title("📰 Automatic Political Retractions & Corrections Tracker")
st.markdown("**Daily catalog of media self-retractions & corrections in political news** • Newest on top")

df = load_data()

# ====================== MANUAL ENTRY (Main Feature) ======================
st.sidebar.header("➕ Add New Entry")
with st.sidebar.expander("Add a New Retraction / Correction", expanded=True):
    with st.form("manual_form"):
        title = st.text_input("Retraction Title *")
        outlet = st.text_input("News Outlet * (e.g. New York Times)")
        category = st.selectbox("Category", ["National", "State", "Global/International"])
        original = st.text_area("Original Claim / Story Summary", height=100)
        correction = st.text_area("Retraction / Correction Text *", height=150)
        link = st.text_input("Link to Article")
        views = st.text_input("Estimated Original Views (optional)")
        
        if st.form_submit_button("Add to Database"):
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
                st.success("✅ Entry added successfully!")
                st.rerun()
            else:
                st.error("Title, Outlet, and Correction text are required.")

# Light Auto Search
st.sidebar.header("🔄 Auto Search")
if st.sidebar.button("🔍 Run Quick Auto Search"):
    st.info("Auto search is limited. For best results, use Manual Entry above.")

# ====================== MAIN DISPLAY ======================
st.subheader("Recent Retractions & Corrections")

if df.empty:
    st.info("No entries yet. Use the sidebar to add your first retraction.")
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
                    st.caption(f"**{row['Formatted_Date']}**")
                    st.markdown(f"**{row['Outlet']}**")
                    st.markdown(f"**[{row['Title']}]({row['Link']})**")
                    
                    st.markdown("**🔴 Retraction / Correction**")
                    st.write(row["Correction"])
                    
                    st.markdown("**Original Story**")
                    st.write(row["Original_Claim"])
                    
                    if row.get("Views_Estimate") and row["Views_Estimate"] != "N/A":
                        st.caption(f"📊 Est. Original Views: {row['Views_Estimate']}")
                    
                    st.caption(f"Source: {row['Source']}")

# Disclaimer
st.markdown("---")
st.caption("""
**Disclaimer**: This app collects self-retractions and corrections published by media outlets. 
It is **not** a fact-checking service. Always read the original articles for full context.
""")