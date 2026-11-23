import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
MODELS, DATA, REPORTS = ROOT / "models", ROOT / "data", ROOT / "reports"

st.set_page_config(page_title="Diabetes Risk Assessment", page_icon="🩺", layout="wide")

# ---------- loading ----------
@st.cache_resource
def load_model():
    model = joblib.load(MODELS / "xgb_model.pkl")
    features = joblib.load(MODELS / "feature_names.pkl")
    settings = json.load(open(MODELS / "settings.json"))
    return model, features, settings

@st.cache_data
def load_data():
    return pd.read_csv(DATA / "brfss2024_8features.csv")

model, FEATURES, SETTINGS = load_model()
LOW_MAX, HIGH_MIN = SETTINGS["low_max"], SETTINGS["high_min"]

# ---------- label tables ----------
AGE = {"18-24": 1, "25-29": 2, "30-34": 3, "35-39": 4, "40-44": 5, "45-49": 6, "50-54": 7,
       "55-59": 8, "60-64": 9, "65-69": 10, "70-74": 11, "75-79": 12, "80 or older": 13}
HEALTH = {"Excellent": 1, "Very good": 2, "Good": 3, "Fair": 4, "Poor": 5}
INCOME = {"Less than $10,000": 1, "$10,000 - $15,000": 2, "$15,000 - $20,000": 3,
          "$20,000 - $25,000": 4, "$25,000 - $35,000": 5, "$35,000 - $50,000": 6,
          "$50,000 - $75,000": 7, "$75,000 - $100,000": 8, "$100,000 - $150,000": 9,
          "$150,000 - $200,000": 10, "$200,000 or more": 11}
NICE = {"_AGEG5YR": "Age group", "GENHLTH": "General health", "_BMI5": "BMI", "_MICHD": "Heart disease",
        "DIFFWALK": "Difficulty walking", "EXERANY2": "Exercise", "INCOME3": "Income", "PHYSHLTH": "Poor physical health days"}

def risk_level(p):
    if p < LOW_MAX:
        return "Low", "#2E7D5B"
    if p < HIGH_MIN:
        return "Moderate", "#D98E04"
    return "High", "#C0392B"

def build_row(age, health, bmi, heart, walk, exercise, income, phys):
    values = {"_AGEG5YR": age, "GENHLTH": health, "_BMI5": bmi, "_MICHD": heart,
              "DIFFWALK": walk, "EXERANY2": exercise, "INCOME3": income, "PHYSHLTH": phys}
    return pd.DataFrame([values])[FEATURES]

def gauge(p):
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=p * 100, number={"suffix": "%", "valueformat": ".1f"},
        gauge={"axis": {"range": [0, 60]}, "bar": {"color": "#1F3A5F"},
               "steps": [{"range": [0, LOW_MAX * 100], "color": "#BFE3D0"},
                         {"range": [LOW_MAX * 100, HIGH_MIN * 100], "color": "#F8E0A8"},
                         {"range": [HIGH_MIN * 100, 60], "color": "#F2B8B0"}]}))
    fig.update_layout(height=280, margin=dict(l=20, r=20, t=30, b=10))
    return fig

# ---------- sidebar ----------
st.sidebar.title("🩺 Diabetes Risk")
page = st.sidebar.radio("Go to", ["Risk Predictor", "Data Explorer", "Model Performance"])
st.sidebar.info("Screening aid only. This is not a medical diagnosis. "
                "Please consult a doctor for a blood test.")

# ================= PAGE 1 =================
if page == "Risk Predictor":
    st.title("Diabetes Risk Predictor")
    st.caption("Based on the CDC BRFSS 2024 survey (441,934 adults). Answer the questions and press the button.")

    c1, c2 = st.columns(2)
    with c1:
        age_label = st.selectbox("Age group", list(AGE.keys()), index=6)
        health_label = st.selectbox("How is your general health?", list(HEALTH.keys()), index=2)
        height = st.number_input("Height (cm)", 120.0, 220.0, 165.0, step=1.0)
        weight = st.number_input("Weight (kg)", 30.0, 250.0, 70.0, step=1.0)
        income_label = st.selectbox("Household income group", list(INCOME.keys()), index=6)
    with c2:
        phys = st.slider("Days of poor physical health in the last 30 days", 0, 30, 0)
        exercise = st.radio("Any physical activity or exercise in the past month?", ["Yes", "No"], horizontal=True)
        walk = st.radio("Serious difficulty walking or climbing stairs?", ["No", "Yes"], horizontal=True)
        heart = st.radio("Ever told you have coronary heart disease or had a heart attack?", ["No", "Yes"], horizontal=True)

    bmi = round(weight / ((height / 100) ** 2), 1)
    st.write(f"Calculated BMI: **{bmi}**")

    if st.button("Calculate my risk", type="primary"):
        row = build_row(AGE[age_label], HEALTH[health_label], bmi, int(heart == "Yes"),
                        int(walk == "Yes"), int(exercise == "Yes"), INCOME[income_label], phys)
        prob = float(model.predict_proba(row)[0][1])
        level, color = risk_level(prob)

        left, right = st.columns([1, 1])
        with left:
            st.plotly_chart(gauge(prob), use_container_width=True)
        with right:
            st.markdown(f"### Risk level: <span style='color:{color}'>{level}</span>", unsafe_allow_html=True)
            st.write(f"Estimated chance of diabetes: **{prob * 100:.1f}%**")
            st.write("For comparison, about **14.9%** of adults in the survey have diabetes.")
            if level == "High":
                st.warning("Consider getting a blood sugar test (fasting glucose or HbA1c) soon.")
            elif level == "Moderate":
                st.info("Consider a routine check-up and discuss your risk with a doctor.")
            else:
                st.success("Keep up healthy habits and have regular check-ups.")

        st.subheader("Why this result?")
        try:
            import shap
            explainer = shap.TreeExplainer(model)
            sv = explainer.shap_values(row)[0]
            exp = pd.DataFrame({"Factor": [NICE[f] for f in FEATURES], "Effect": sv}).sort_values("Effect")
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.barh(exp["Factor"], exp["Effect"], color=["#2E7D5B" if v < 0 else "#C0392B" for v in exp["Effect"]])
            ax.axvline(0, color="grey", linewidth=0.8)
            ax.set_xlabel("Effect on risk (red raises risk, green lowers it)")
            plt.tight_layout()
            st.pyplot(fig)
        except Exception as e:
            st.caption(f"Explanation chart unavailable: {e}")

        st.subheader("Healthy-habit tips")
        st.markdown("- Aim for at least 150 minutes of moderate activity per week.\n"
                    "- Choose whole grains, vegetables and fewer sugary drinks.\n"
                    "- Keep your weight in a healthy range.\n"
                    "- Get regular blood sugar checks if you are over 35 or have risk factors.")

# ================= PAGE 2 =================
elif page == "Data Explorer":
    st.title("Data Explorer")
    df = load_data()
    age_names = {v: k for k, v in AGE.items()}
    health_names = {v: k for k, v in HEALTH.items()}

    a, b, c = st.columns(3)
    a.metric("People in dataset", f"{len(df):,}")
    b.metric("With diabetes", f"{df['Outcome'].mean() * 100:.1f}%")
    c.metric("Average BMI", f"{df['_BMI5'].mean():.1f}")

    age_rate = (df.groupby("_AGEG5YR")["Outcome"].mean() * 100).reset_index()
    age_rate["Age group"] = age_rate["_AGEG5YR"].map(age_names)
    st.plotly_chart(px.bar(age_rate, x="Age group", y="Outcome", title="Diabetes rate by age group",
                           labels={"Outcome": "% with diabetes"}), use_container_width=True)

    h_rate = (df.groupby("GENHLTH")["Outcome"].mean() * 100).reset_index()
    h_rate["General health"] = h_rate["GENHLTH"].map(health_names)
    st.plotly_chart(px.bar(h_rate, x="General health", y="Outcome", title="Diabetes rate by self-rated health",
                           labels={"Outcome": "% with diabetes"}), use_container_width=True)

    sample = df.dropna(subset=["_BMI5"]).sample(20000, random_state=1)
    sample["Status"] = sample["Outcome"].map({0: "No diabetes", 1: "Diabetes"})
    st.plotly_chart(px.histogram(sample[sample["_BMI5"] < 60], x="_BMI5", color="Status", barmode="overlay",
                                 opacity=0.6, nbins=50, title="BMI distribution", labels={"_BMI5": "BMI"}),
                    use_container_width=True)

# ================= PAGE 3 =================
else:
    st.title("Model Performance")
    st.write("Four models were trained on the same 80/20 split. Scores are on the 20% test set (about 88,000 people).")
    st.dataframe(pd.read_csv(REPORTS / "model_comparison.csv"), use_container_width=True, hide_index=True)

    st.subheader("Screening thresholds")
    st.write("A lower threshold catches more real cases (higher recall) but flags more people.")
    st.dataframe(pd.read_csv(REPORTS / "threshold_table.csv"), use_container_width=True, hide_index=True)

    st.subheader("Do the risk levels mean something?")
    st.dataframe(pd.read_csv(REPORTS / "risk_band_table.csv"), use_container_width=True, hide_index=True)

    for name, title in [("shap_bar.png", "Most important factors (SHAP)"), ("shap_summary.png", "How each factor pushes risk")]:
        if (REPORTS / name).exists():
            st.subheader(title)
            st.image(str(REPORTS / name))

    st.subheader("Limitations")
    st.markdown("- Self-reported survey data with no lab values such as glucose or HbA1c.\n"
                "- Shows patterns in this survey, not causes.\n"
                "- Screening aid only, not a medical diagnosis.")
