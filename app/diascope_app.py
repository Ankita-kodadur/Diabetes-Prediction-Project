"""DiaScope - Diabetes Risk Intelligence (Streamlit dashboard)
Run from the project folder:  streamlit run app\\diascope_app.py
"""
import datetime
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
MODELS, DATA, REPORTS = ROOT / "models", ROOT / "data", ROOT / "reports"

st.set_page_config(page_title="DiaScope - Diabetes Risk Intelligence", page_icon="🩺", layout="wide")

# ---------------------------------------------------------------- look & feel
TEAL, DEEP, CORAL, GREY = "#0F766E", "#134E4A", "#F97316", "#94A3B8"
LIGHT = dict(bg="#F4F8F7", side="#E2EEEB", text="#12302D", card="#FFFFFF", cardtext="#12302D",
             border="#DCE9E6", muted="#5B6F6C", big="#134E4A", input="#FFFFFF", grid="rgba(18,48,45,0.12)",
             row="#FFFFFF")
DARK = dict(bg="#0B1B1A", side="#102B28", text="#E6F4F1", card="#13302D", cardtext="#E6F4F1",
            border="#1F4A45", muted="#9CC5BF", big="#5EEAD4", input="#16403B", grid="rgba(230,244,241,0.14)",
            row="#0F2927")

with st.sidebar:
    dark = st.toggle("🌙 Dark mode", value=False)
P = DARK if dark else LIGHT

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap');
.stApp h1, .stApp h2, .stApp h3, .hero, .card, .stTabs button p { font-family: 'Poppins', sans-serif; }
.block-container { padding-top: 1.6rem; max-width: 1250px; }
.hero { background: linear-gradient(120deg, #0F766E 0%, #115E59 55%, #134E4A 100%);
        padding: 26px 34px; border-radius: 20px; color: #ffffff; margin-bottom: 18px; }
.hero-title { font-size: 2.1rem; font-weight: 700; line-height: 1.15; }
.hero-sub { opacity: .92; margin-top: 6px; font-size: 1rem; }
.hero-tag { display:inline-block; background: rgba(255,255,255,.16); padding: 3px 12px;
            border-radius: 999px; font-size: .78rem; margin-bottom: 10px; letter-spacing: .6px; }
.card { background: %card%; color: %cardtext%; border-radius: 18px; padding: 20px 24px;
        box-shadow: 0 3px 14px rgba(15,118,110,.14); border: 1px solid %border%; }
.card-label { color: %muted%; font-size:.78rem; letter-spacing:.8px; text-transform:uppercase; }
.pill { display:inline-block; padding: 6px 18px; border-radius: 999px; color:#fff !important;
        font-weight:600; font-size:1.05rem; margin: 6px 0 10px 0; }
.big { font-size: 2.7rem; font-weight: 700; line-height: 1.05; color: %big%; }
.muted { color: %muted%; font-size:.9rem; }
.stTabs [data-baseweb="tab"] { font-weight: 600; }
"""

DARK_CSS = """
.stApp, [data-testid="stAppViewContainer"] { background-color: %bg% !important; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div { background-color: %side% !important; }
[data-testid="stHeader"] { background-color: %bg% !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp label, .stApp li, .stApp span,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"], [data-testid="stMarkdownContainer"] { color: %text%; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: %muted% !important; }
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="base-input"],
[data-testid="stNumberInput"] input, [data-testid="stNumberInput"] button
{ background-color: %input% !important; color: %text% !important; }
[data-baseweb="popover"], [data-baseweb="popover"] ul, [data-baseweb="menu"] { background-color: %input% !important; }
[data-baseweb="popover"] li, [data-baseweb="popover"] li * { color: %text% !important; }
[data-testid="stAlert"] { background-color: %card% !important; }
[data-testid="stVerticalBlockBorderWrapper"] { border-color: %border% !important; }
[data-testid="stDownloadButton"] button, .stButton button
{ background-color: %input% !important; color: %text% !important; border-color: %border% !important; }
[data-testid="stDownloadButton"] button p { color: %text% !important; }
[data-testid="stExpander"] details { background-color: %card%; border-color: %border%; }
.stTabs [data-baseweb="tab-list"] { border-bottom-color: %border%; }
.stApp .pill, .stApp .pill * { color: #ffffff !important; }
.stApp .hero, .stApp .hero * { color: #ffffff; }
"""

css = BASE_CSS + (DARK_CSS if dark else "")
for k, v in P.items():
    css = css.replace("%" + k + "%", v)
st.markdown("<style>" + css + "</style>", unsafe_allow_html=True)

import auth
USER = auth.require_login()   # shows the login page and stops until the user signs in

# ---------------------------------------------------------------- loading
@st.cache_resource
def load_model():
    model = joblib.load(MODELS / "xgb_model.pkl")
    features = joblib.load(MODELS / "feature_names.pkl")
    settings = json.load(open(MODELS / "settings.json"))
    return model, features, settings

@st.cache_data
def load_data():
    return pd.read_csv(DATA / "brfss2024_8features.csv")

@st.cache_resource
def get_explainer():
    import shap
    return shap.TreeExplainer(model)

model, FEATURES, SETTINGS = load_model()
DF = load_data()
LOW_MAX, HIGH_MIN = SETTINGS["low_max"], SETTINGS["high_min"]
BASE_RATE = float(DF["Outcome"].mean())

# ---------------------------------------------------------------- labels
AGE = {"18-24": 1, "25-29": 2, "30-34": 3, "35-39": 4, "40-44": 5, "45-49": 6, "50-54": 7,
       "55-59": 8, "60-64": 9, "65-69": 10, "70-74": 11, "75-79": 12, "80 or older": 13}
AGE_NAME = {v: k for k, v in AGE.items()}
HEALTH = {"Excellent": 1, "Very good": 2, "Good": 3, "Fair": 4, "Poor": 5}
HEALTH_NAME = {v: k for k, v in HEALTH.items()}
INCOME = {"Less than $10,000": 1, "$10,000 - $15,000": 2, "$15,000 - $20,000": 3,
          "$20,000 - $25,000": 4, "$25,000 - $35,000": 5, "$35,000 - $50,000": 6,
          "$50,000 - $75,000": 7, "$75,000 - $100,000": 8, "$100,000 - $150,000": 9,
          "$150,000 - $200,000": 10, "$200,000 or more": 11}
NICE = {"_AGEG5YR": "Age group", "GENHLTH": "General health", "_BMI5": "BMI", "_MICHD": "Heart disease",
        "DIFFWALK": "Difficulty walking", "EXERANY2": "Exercise", "INCOME3": "Income",
        "PHYSHLTH": "Poor physical health days"}

# ---------------------------------------------------------------- helpers
def predict(frame):
    return model.predict_proba(frame[FEATURES])[:, 1]

def one_row(profile):
    return pd.DataFrame([profile])[FEATURES]

def variants(profile, key, values):
    d = pd.DataFrame([profile] * len(values))
    d[key] = list(values)
    return d[FEATURES]

def show_table(df):
    d = df.copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda v: f"{v:.3f}".rstrip("0").rstrip(".") if pd.notna(v) else "")
    head = "".join(f"<th style='text-align:left;padding:9px 12px;background:#0F766E;color:#ffffff'>{c}</th>"
                   for c in d.columns)
    cell = f"padding:8px 12px;border-bottom:1px solid {P['border']};color:{P['text']};background:{P['row']}"
    rows = "".join("<tr>" + "".join(f"<td style='{cell}'>{v}</td>" for v in r) + "</tr>"
                   for r in d.itertuples(index=False))
    st.markdown(f"<div style='overflow-x:auto'><table style='width:100%;border-collapse:collapse;font-size:.9rem'>"
                f"<tr>{head}</tr>{rows}</table></div>", unsafe_allow_html=True)


def esc(v):
    """Escape dollar signs so Streamlit does not treat them as math formatting."""
    return str(v).replace("$", "\\$")

def level_of(p):
    if p < LOW_MAX:
        return "Low", "#16A34A", "Your answers resemble people who rarely have diabetes. Keep up healthy habits and have routine check-ups."
    if p < HIGH_MIN:
        return "Moderate", "#D97706", "Your answers are in the middle range. A routine check-up and a chat with a doctor about your risk is a good idea."
    return "High", "#DC2626", "Your answers resemble people who often have diabetes. Consider a blood sugar test (fasting glucose or HbA1c) soon."

def bmi_band(b):
    if b < 18.5: return "Underweight"
    if b < 25: return "Normal range"
    if b < 30: return "Overweight"
    return "Obese range"

def style(fig, h=330):
    fig.update_layout(height=h, margin=dict(l=10, r=10, t=40, b=10), paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Poppins, sans-serif", color=P["text"]))
    fig.update_xaxes(gridcolor=P["grid"])
    fig.update_yaxes(gridcolor=P["grid"])
    return fig

def gauge(p):
    top = max(60, int(np.ceil(p * 100 / 10) * 10))
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=p * 100, number={"suffix": "%", "valueformat": ".1f", "font": {"color": P["text"]}},
        gauge={"axis": {"range": [0, top]}, "bar": {"color": DEEP, "thickness": 0.28},
               "steps": [{"range": [0, LOW_MAX * 100], "color": "#BBF7D0"},
                         {"range": [LOW_MAX * 100, HIGH_MIN * 100], "color": "#FDE68A"},
                         {"range": [HIGH_MIN * 100, top], "color": "#FECACA"}]}))
    return style(fig, 290)

def explain(row):
    try:
        sv = get_explainer().shap_values(row)[0]
        return pd.DataFrame({"Code": FEATURES, "Factor": [NICE[f] for f in FEATURES], "Effect": sv})
    except Exception:
        return None

def peer_stats(age_code, health_code):
    m = DF[(DF["_AGEG5YR"] == age_code) & (DF["GENHLTH"] == health_code)]
    return len(m), (float(m["Outcome"].mean()) if len(m) else float("nan"))

# ---------------------------------------------------------------- sidebar: profile builder
with st.sidebar:
    st.markdown("### 🧬 Build your profile")
    st.caption("Everything updates live as you change an answer.")
    age_label = st.selectbox("Age group", list(AGE), index=6)
    health_label = st.selectbox("General health", list(HEALTH), index=2)
    height = st.number_input("Height (cm)", 120.0, 220.0, 165.0, 1.0)
    weight = st.number_input("Weight (kg)", 30.0, 250.0, 70.0, 1.0)
    income_label = st.selectbox("Household income group", list(INCOME), index=6)
    phys = st.slider("Poor physical health days (last 30)", 0, 30, 0)
    exercise = st.radio("Any exercise in the past month?", ["Yes", "No"], index=0, horizontal=True)
    walk = st.radio("Serious difficulty walking?", ["No", "Yes"], index=0, horizontal=True)
    heart = st.radio("Heart disease or heart attack?", ["No", "Yes"], index=0, horizontal=True)
    bmi = round(weight / ((height / 100) ** 2), 1)
    st.info(f"BMI **{bmi}**  ({bmi_band(bmi)})")

profile = {"_AGEG5YR": AGE[age_label], "GENHLTH": HEALTH[health_label], "_BMI5": bmi,
           "_MICHD": int(heart == "Yes"), "DIFFWALK": int(walk == "Yes"),
           "EXERANY2": int(exercise == "Yes"), "INCOME3": INCOME[income_label], "PHYSHLTH": phys}
answers = {"Age group": age_label, "General health": health_label, "BMI": f"{bmi} ({bmi_band(bmi)})",
           "Heart disease": heart, "Difficulty walking": walk, "Exercise": exercise,
           "Income": income_label, "Poor physical health days": str(phys)}

prob = float(predict(one_row(profile))[0])
level, color, advice = level_of(prob)
exp = explain(one_row(profile))
n_peers, peer_rate = peer_stats(profile["_AGEG5YR"], profile["GENHLTH"])

def build_report():
    css = ("body{font-family:Arial,sans-serif;max-width:720px;margin:30px auto;color:#12302D}"
           "h1{color:#0F766E}table{border-collapse:collapse;width:100%}td{border:1px solid #cfe0dc;padding:8px}"
           ".box{background:#F0FAF8;border-radius:10px;padding:14px;margin:14px 0}")
    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in answers.items())
    drivers = ""
    if exp is not None:
        top = exp.reindex(exp["Effect"].abs().sort_values(ascending=False).index).head(3)
        drivers = "<h3>Main factors behind this result</h3><ul>" + "".join(
            f"<li>{r.Factor}: {'raises' if r.Effect > 0 else 'lowers'} the estimated risk</li>"
            for r in top.itertuples()) + "</ul>"
    return (f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>"
            f"<h1>DiaScope Risk Report</h1><p>Generated {datetime.date.today():%d %B %Y}</p>"
            f"<div class='box'><b>Risk level: {level}</b><br>Estimated chance of diabetes: <b>{prob * 100:.1f}%</b>"
            f" (average adult in the survey: {BASE_RATE * 100:.1f}%)</div>"
            f"<h3>Your answers</h3><table>{rows}</table>{drivers}<p>{advice}</p>"
            f"<p><i>Screening aid based on the CDC BRFSS 2024 survey. Not a medical diagnosis. "
            f"Please consult a doctor for a blood test.</i></p></body></html>")

with st.sidebar:
    st.caption(f"Signed in as **{USER}**")
    if st.button("💾 Save this result to my history"):
        auth.add_history(USER, prob * 100, level, bmi, answers)
        st.toast("Saved to your history")
    st.download_button("📄 Download my report", data=build_report(), file_name="DiaScope_risk_report.html",
                       mime="text/html")
    if st.button("Log out"):
        auth.logout()
    st.caption("Screening aid only. Not a medical diagnosis.")

# ---------------------------------------------------------------- hero + headline result
st.markdown("""
<div class="hero">
  <div class="hero-tag">MACHINE LEARNING  ·  CDC BRFSS 2024  ·  441,934 ADULTS</div>
  <div class="hero-title">DiaScope</div>
  <div class="hero-sub">Diabetes risk intelligence: see your risk, understand the reasons, and explore what could change it.</div>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1.15, 1])
with left:
    st.plotly_chart(gauge(prob), use_container_width=True)
with right:
    times = prob / BASE_RATE
    peer_line = (f"Among {n_peers:,} survey adults with your age group and health rating, "
                 f"<b>{peer_rate * 100:.1f}%</b> have diabetes.") if n_peers else ""
    st.markdown(f"""
    <div class="card">
      <div class="card-label">Your risk level</div>
      <span class="pill" style="background:{color}">{level}</span>
      <div class="big">{prob * 100:.1f}%</div>
      <div class="muted">About {prob * 100:.0f} in 100 people with a profile like yours are expected to have diabetes.
      That is <b>{times:.1f}x</b> the average adult ({BASE_RATE * 100:.1f}%).</div>
      <div class="muted" style="margin-top:8px">{peer_line}</div>
      <div style="margin-top:12px">{advice}</div>
    </div>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🔍 Why this result", "🧪 What-if Lab", "⏳ Age Journey", "👥 People like you",
                "📊 Data Insights", "⚙️ Model Lab", "🗂️ My history"])

# ---------------------------------------------------------------- tab 1: why
with tabs[0]:
    st.subheader("What is driving your result?")
    if exp is None:
        st.warning("The explanation module (SHAP) is not available, so this chart cannot be drawn.")
    else:
        e = exp.sort_values("Effect")
        fig = go.Figure(go.Bar(x=e["Effect"], y=e["Factor"], orientation="h",
                               marker_color=[TEAL if v < 0 else CORAL for v in e["Effect"]]))
        fig.update_layout(title="Orange pushes risk up, teal pushes risk down", xaxis_title="Strength of effect")
        st.plotly_chart(style(fig, 380), use_container_width=True)
        up = exp[exp["Effect"] > 0].sort_values("Effect", ascending=False)
        down = exp[exp["Effect"] < 0].sort_values("Effect")
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                st.markdown("**Raising your risk**")
                if len(up):
                    for r in up.head(3).itertuples():
                        st.write(f"• {r.Factor}: {esc(answers.get(r.Factor, ''))}")
                else:
                    st.write("Nothing in your profile raises your risk above average.")
        with c2:
            with st.container(border=True):
                st.markdown("**Lowering your risk**")
                if len(down):
                    for r in down.head(3).itertuples():
                        st.write(f"• {r.Factor}: {esc(answers.get(r.Factor, ''))}")
                else:
                    st.write("Nothing in your profile lowers your risk below average.")
        st.caption("Bars show relative strength inside the model, not percentages.")

# ---------------------------------------------------------------- tab 2: what-if
with tabs[1]:
    st.subheader("What-if Lab: try changing a habit")
    c1, c2, c3 = st.columns(3)
    with c1:
        new_bmi = st.slider("If my BMI were...", 15.0, 50.0, float(min(max(bmi, 15.0), 50.0)), 0.5)
    with c2:
        new_ex = st.toggle("What if I exercised regularly?", value=(exercise == "Yes"))
    with c3:
        new_phys = st.slider("If my poor-health days were...", 0, 30, int(phys))
    scenario = dict(profile, _BMI5=new_bmi, EXERANY2=int(new_ex), PHYSHLTH=new_phys)
    sprob = float(predict(one_row(scenario))[0])
    slevel, scolor, _ = level_of(sprob)
    m1, m2, m3 = st.columns(3)
    m1.metric("Current risk", f"{prob * 100:.1f}%")
    m2.metric("Scenario risk", f"{sprob * 100:.1f}%", f"{(sprob - prob) * 100:+.1f} points", delta_color="inverse")
    m3.metric("Scenario level", slevel)

    bmis = np.arange(15.0, 50.5, 1.0)
    curve = predict(variants(profile, "_BMI5", bmis)) * 100
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=bmis, y=curve, mode="lines", name="Risk at each BMI", line=dict(color=TEAL, width=3)))
    fig.add_trace(go.Scatter(x=[bmi], y=[prob * 100], mode="markers", name="You now",
                             marker=dict(size=13, color=DEEP)))
    fig.add_trace(go.Scatter(x=[new_bmi], y=[sprob * 100], mode="markers", name="Scenario",
                             marker=dict(size=13, color=CORAL, symbol="diamond")))
    fig.update_layout(title="Your estimated risk across BMI values (other answers unchanged)",
                      xaxis_title="BMI", yaxis_title="Estimated risk (%)")
    st.plotly_chart(style(fig, 360), use_container_width=True)
    st.caption("These are patterns found in survey data, not a promise of what will happen to one person. "
               "Talk to a doctor before changing your health routine.")

# ---------------------------------------------------------------- tab 3: age journey
with tabs[2]:
    st.subheader("Age Journey: how risk changes as you get older")
    ages = list(AGE.values())
    mine = predict(variants(profile, "_AGEG5YR", ages)) * 100
    pop = (DF.groupby("_AGEG5YR")["Outcome"].mean() * 100).reindex(ages).values
    labels = [AGE_NAME[a] for a in ages]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=labels, y=mine, mode="lines+markers", name="Your profile (if nothing else changes)",
                             line=dict(color=CORAL, width=3)))
    fig.add_trace(go.Scatter(x=labels, y=pop, mode="lines+markers", name="Average adult in the survey",
                             line=dict(color=GREY, width=3, dash="dot")))
    fig.update_layout(yaxis_title="Estimated risk (%)", xaxis_title="Age group")
    st.plotly_chart(style(fig, 380), use_container_width=True)
    future = st.select_slider("Look ahead to age group", options=list(AGE), value=age_label)
    fpct = float(mine[ages.index(AGE[future])])
    st.info(f"If your other answers stayed the same, your estimated risk at **{future}** would be "
            f"**{fpct:.1f}%** ({level_of(fpct / 100)[0]}).")
    st.caption("Holding everything else constant is a simplification, since health usually changes with age.")

# ---------------------------------------------------------------- tab 4: peers
with tabs[3]:
    st.subheader("People like you")
    if n_peers:
        a, b, c = st.columns(3)
        a.metric("Survey adults with your age group and health", f"{n_peers:,}")
        b.metric("Real diabetes rate in that group", f"{peer_rate * 100:.1f}%")
        c.metric("All adults in the survey", f"{BASE_RATE * 100:.1f}%")
        fig = go.Figure(go.Bar(x=["Your model estimate", "People like you (real)", "All adults (real)"],
                               y=[prob * 100, peer_rate * 100, BASE_RATE * 100],
                               marker_color=[CORAL, TEAL, GREY]))
        fig.update_layout(yaxis_title="% with diabetes")
        st.plotly_chart(style(fig, 340), use_container_width=True)
        st.caption("The model also uses BMI, income, exercise and more, so its estimate can differ from the simple group rate.")
    else:
        st.write("No survey adults match this age group and health rating.")

# ---------------------------------------------------------------- tab 5: data insights
with tabs[4]:
    st.subheader("What the survey data shows")
    ages = list(AGE.values())
    rate_age = (DF.groupby("_AGEG5YR")["Outcome"].mean() * 100).reindex(ages)
    fig = go.Figure(go.Bar(x=[AGE_NAME[a] for a in ages], y=rate_age.values, marker_color=TEAL))
    fig.update_layout(title="Diabetes rate by age group", yaxis_title="% with diabetes")
    st.plotly_chart(style(fig), use_container_width=True)

    hs = list(HEALTH.values())
    rate_h = (DF.groupby("GENHLTH")["Outcome"].mean() * 100).reindex(hs)
    fig = go.Figure(go.Bar(x=[HEALTH_NAME[h] for h in hs], y=rate_h.values, marker_color=CORAL))
    fig.update_layout(title="Diabetes rate by self-rated general health", yaxis_title="% with diabetes")
    st.plotly_chart(style(fig), use_container_width=True)

    samp = DF.dropna(subset=["_BMI5"]).sample(30000, random_state=1)
    samp = samp[samp["_BMI5"] < 60]
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=samp[samp["Outcome"] == 0]["_BMI5"], name="No diabetes", marker_color=GREY,
                               opacity=0.65, nbinsx=50))
    fig.add_trace(go.Histogram(x=samp[samp["Outcome"] == 1]["_BMI5"], name="Diabetes", marker_color=CORAL,
                               opacity=0.75, nbinsx=50))
    fig.update_layout(barmode="overlay", title="BMI distribution", xaxis_title="BMI", yaxis_title="People")
    st.plotly_chart(style(fig), use_container_width=True)

# ---------------------------------------------------------------- tab 6: model lab
with tabs[5]:
    st.subheader("Model Lab")
    st.markdown("**Screening Lab: where should the alert line be?**")
    thr = pd.read_csv(REPORTS / "threshold_table.csv")
    options = [float(x) for x in thr["Threshold"]]
    default = min(options, key=lambda x: abs(x - SETTINGS.get("threshold", 0.15)))
    pick = st.select_slider("Flag a person when their risk is at least", options=options, value=default,
                            format_func=lambda x: f"{x * 100:.0f}%")
    r = thr[np.isclose(thr["Threshold"], pick)].iloc[0]
    a, b, c = st.columns(3)
    a.metric("Real cases caught (recall)", f"{r['Recall'] * 100:.0f}%")
    b.metric("Flagged people who truly have diabetes", f"{r['Precision'] * 100:.0f}%")
    c.metric("Share of everyone flagged", f"{r['% of people flagged']:.0f}%")
    st.info(f"At this setting, out of 1,000 people who truly have diabetes, about "
            f"**{r['Recall'] * 1000:.0f}** would be flagged. A lower line catches more cases but flags more people.")

    st.markdown("**Model comparison (test set)**")
    show_table(pd.read_csv(REPORTS / "model_comparison.csv"))
    st.markdown("**Do the risk levels mean something?**")
    show_table(pd.read_csv(REPORTS / "risk_band_table.csv"))

    for fname, cap in [("roc_curves.png", "ROC curves of all models"), ("shap_bar.png", "Most important factors"),
                       ("shap_summary.png", "How each factor pushes risk")]:
        if (REPORTS / fname).exists():
            st.image(str(REPORTS / fname), caption=cap)

    with st.expander("Limitations"):
        st.markdown("- Self-reported survey data with no lab values such as glucose or HbA1c.\n"
                    "- Shows patterns in this survey, not causes.\n"
                    "- Screening aid only, not a medical diagnosis.")

# ---------------------------------------------------------------- tab 7: my history
with tabs[6]:
    st.subheader("My history")
    hist = auth.get_history(USER)
    if hist.empty:
        st.info("Nothing saved yet. Use 'Save this result to my history' in the left panel after you check your risk.")
    else:
        fig = go.Figure(go.Scatter(x=hist["Date"], y=hist["Risk %"], mode="lines+markers", line=dict(color=TEAL, width=3)))
        fig.update_layout(title="Your saved risk over time", yaxis_title="Estimated risk (%)")
        st.plotly_chart(style(fig, 320), use_container_width=True)
        show_table(hist.iloc[::-1].reset_index(drop=True))
        if st.button("Clear my history"):
            auth.clear_history(USER)
            st.rerun()
