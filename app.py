import streamlit as st
import couchdb
import os
import re
import json
import pandas as pd
import uuid

st.set_page_config(page_title="MedInsight", layout="wide")

# =========================
# DATABASE CONNECTION (FIXED)
# =========================

@st.cache_resource
def get_db():
    couch = couchdb.Server("http://admin:admin@couchdb:5984/")
    couch.resource.credentials = ("admin", "admin")  # ✅ FIX

    db_name = "medical_analyzer"

    if db_name not in couch:
        couch.create(db_name)

    return couch[db_name]

db = get_db()

# =========================
# FILE STORAGE
# =========================

if not os.path.exists("reports"):
    os.makedirs("reports")

# =========================
# EXTRACTION
# =========================

def extract_values(file):
    content = file.read().decode("utf-8")

    def find(pattern):
        m = re.search(pattern, content, re.IGNORECASE)
        return int(m.group(1)) if m else None

    return {
        "glucose": find(r"Glucose\s*:\s*(\d+)"),
        "cholesterol": find(r"Cholesterol\s*:\s*(\d+)"),
        "hemoglobin": find(r"Hemoglobin\s*:\s*(\d+)"),
        "bp": find(r"BP\s*:\s*(\d+)")
    }

# =========================
# ANALYSIS (UNCHANGED 🔥)
# =========================

def analyze(data):
    score = 0
    issues = []

    if data["glucose"] > 160:
        score += 2
        issues.append("High Blood Sugar")
    elif data["glucose"] > 120:
        score += 1

    if data["cholesterol"] > 240:
        score += 2
        issues.append("High Cholesterol")
    elif data["cholesterol"] > 200:
        score += 1

    if data["hemoglobin"] < 11:
        score += 2
        issues.append("Low Hemoglobin")

    if data["bp"] > 140:
        score += 2
        issues.append("High Blood Pressure")
    elif data["bp"] > 120:
        score += 1

    if score >= 5:
        return "High", issues
    elif score >= 3:
        return "Moderate", issues
    return "Low", issues


def get_recommendation(risk):
    if risk == "High":
        return ["Consult doctor immediately", "Strict diet control", "Monitor daily"]
    elif risk == "Moderate":
        return ["Exercise daily", "Reduce sugar/fat", "Check again in 2 weeks"]
    return ["Maintain healthy lifestyle"]

# =========================
# DATABASE FUNCTIONS
# =========================

def register_patient(pid, name, age, gender):
    doc = {
        "_id": f"patient_{pid}",
        "type": "patient",
        "name": name,
        "age": age,
        "gender": gender
    }
    try:
        db.save(doc)
        return True
    except:
        return False


def save_report(pid, data):
    doc = {
        "_id": str(uuid.uuid4()),
        "type": "report",
        "patient_id": pid,
        "data": data,
        "date": str(pd.Timestamp.now())
    }
    db.save(doc)


def get_reports(pid):
    docs = []
    for doc_id in db:
        doc = db[doc_id]
        if doc.get("type") == "report" and doc.get("patient_id") == pid:
            docs.append(doc)
    return docs


def get_latest_report(pid):
    reports = get_reports(pid)
    if not reports:
        return None
    reports.sort(key=lambda x: x["date"], reverse=True)
    return reports[0]


def save_analysis(pid, risk, issues):
    doc = {
        "_id": str(uuid.uuid4()),
        "type": "analysis",
        "patient_id": pid,
        "risk": risk,
        "issues": issues,
        "date": str(pd.Timestamp.now())
    }
    db.save(doc)


def get_analysis(pid):
    docs = []
    for doc_id in db:
        doc = db[doc_id]
        if doc.get("type") == "analysis" and doc.get("patient_id") == pid:
            docs.append(doc)
    return docs

# =========================
# UI
# =========================

st.title("🩺 MedInsight Dashboard (CouchDB)")

# REGISTER
st.header("1. Patient Registration")

pid = st.text_input("Patient ID")
name = st.text_input("Name")
age = st.number_input("Age", 0, 120)
gender = st.selectbox("Gender", ["Male", "Female", "Other"])

if st.button("Register Patient"):
    if pid and name:
        if register_patient(pid, name, age, gender):
            st.success("Patient registered")
        else:
            st.error("Patient already exists")
    else:
        st.warning("Enter all fields")

# UPLOAD
st.header("2. Upload Report")

file = st.file_uploader("Upload TXT", type=["txt"])

if file:
    if not pid:
        st.error("Enter Patient ID first")
    else:
        file.seek(0)
        data = extract_values(file)
        st.write(data)

        if st.button("Save Report"):
            save_report(pid, data)
            st.success("Report saved")

# ANALYSIS
st.header("3. Risk Analysis")

if st.button("Analyze"):
    report = get_latest_report(pid)

    if report:
        risk, issues = analyze(report["data"])
        rec = get_recommendation(risk)

        save_analysis(pid, risk, issues)

        st.subheader(f"Risk Level: {risk}")

        st.write("### Issues")
        for i in issues:
            st.write("•", i)

        st.write("### Recommendations")
        for r in rec:
            st.write("✔", r)
    else:
        st.error("No report found")

# RECORDS
st.header("4. Records & Trends")

tab1, tab2, tab3 = st.tabs(["Reports", "Analysis", "Trends"])

with tab1:
    if st.button("Show Reports"):
        data = get_reports(pid)
        if data:
            for r in data:
                st.write(r)
        else:
            st.warning("No reports found")

with tab2:
    if st.button("Show Analysis"):
        data = get_analysis(pid)
        if data:
            for d in data:
                st.write(d)
        else:
            st.warning("No analysis found")

with tab3:
    if st.button("Show Trends"):
        reports = get_reports(pid)

        if reports:
            df = pd.DataFrame([{
                "date": r["date"],
                "glucose": r["data"]["glucose"],
                "cholesterol": r["data"]["cholesterol"],
                "hemoglobin": r["data"]["hemoglobin"],
                "bp": r["data"]["bp"]
            } for r in reports])

            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)

            st.line_chart(df)
        else:
            st.warning("No trend data")

st.header("5. Advanced CouchDB Query Console")

query_input = st.text_area(
    "Enter Mango Query (JSON format)",
    '''{
  "selector": {
    "type": "report"
  }
}''',
    height=200
)

if st.button("Run Query"):
    try:
        query = json.loads(query_input)

        results = list(db.find(query))  # 🔥 REAL DB QUERY

        if results:
            st.success(f"{len(results)} results found")
            for r in results:
                st.json(r)
        else:
            st.warning("No results found")

    except Exception as e:
        st.error(f"Error: {str(e)}")