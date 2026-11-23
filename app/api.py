"""DiaScope API v2 - model, features and login for the web dashboard and the mobile app.
Run from the app folder:  uvicorn api:app --host 0.0.0.0 --port 8000
Test page: http://localhost:8000/docs   (use the Authorize button to paste a token from /login)
"""
import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent.parent
MODEL = joblib.load(ROOT / "models" / "xgb_model.pkl")
FEATURES = joblib.load(ROOT / "models" / "feature_names.pkl")
SETTINGS = json.load(open(ROOT / "models" / "settings.json"))
LOW_MAX, HIGH_MIN = SETTINGS["low_max"], SETTINGS["high_min"]
REPORTS, DB_PATH = ROOT / "reports", ROOT / "data" / "users.db"
DF = pd.read_csv(ROOT / "data" / "brfss2024_8features.csv")
BASE_RATE = float(DF["Outcome"].mean())

NICE = {"_AGEG5YR": "Age group", "GENHLTH": "General health", "_BMI5": "BMI", "_MICHD": "Heart disease",
        "DIFFWALK": "Difficulty walking", "EXERANY2": "Exercise", "INCOME3": "Income", "PHYSHLTH": "Poor physical health days"}
AGE = ["18-24", "25-29", "30-34", "35-39", "40-44", "45-49", "50-54", "55-59", "60-64", "65-69", "70-74", "75-79", "80 or older"]
HEALTH = ["Excellent", "Very good", "Good", "Fair", "Poor"]
INCOME = ["Less than $10,000", "$10,000 - $15,000", "$15,000 - $20,000", "$20,000 - $25,000", "$25,000 - $35,000",
          "$35,000 - $50,000", "$50,000 - $75,000", "$75,000 - $100,000", "$100,000 - $150,000", "$150,000 - $200,000", "$200,000 or more"]
ADVICE = {"Low": "Your answers resemble people who rarely have diabetes. Keep up healthy habits and have routine check-ups.",
          "Moderate": "Your answers are in the middle range. A routine check-up and a chat with a doctor about your risk is a good idea.",
          "High": "Your answers resemble people who often have diabetes. Consider a blood sugar test (fasting glucose or HbA1c) soon."}
TIPS = ["Aim for at least 150 minutes of moderate activity per week.", "Choose whole grains, vegetables and fewer sugary drinks.",
        "Keep your weight in a healthy range.", "Get regular blood sugar checks if you are over 35 or have risk factors."]
LIMITS = ["Self-reported survey data with no lab values such as glucose or HbA1c.", "Shows patterns in the survey, not causes.",
          "Screening aid only, not a medical diagnosis."]

# ---- precomputed survey statistics
AGE_RATES = (DF.groupby("_AGEG5YR")["Outcome"].mean() * 100).reindex(range(1, 14)).round(1).tolist()
HEALTH_RATES = (DF.groupby("GENHLTH")["Outcome"].mean() * 100).reindex(range(1, 6)).round(1).tolist()
BMI_LABELS = ["Under 18.5", "18.5-24.9", "25-29.9", "30-34.9", "35-39.9", "40+"]
_bands = pd.cut(DF["_BMI5"], [0, 18.5, 25, 30, 35, 40, 500], right=False, labels=BMI_LABELS)
BMI_RATES = (DF.groupby(_bands, observed=True)["Outcome"].mean() * 100).reindex(BMI_LABELS).round(1).tolist()
PEERS = DF.groupby(["_AGEG5YR", "GENHLTH"])["Outcome"].agg(["count", "mean"])

app = FastAPI(title="DiaScope API", version="2.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ================================================================ users, passwords, tokens
@contextmanager
def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db():
    with _db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
                       salt BLOB NOT NULL, pw_hash BLOB NOT NULL, created TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
                       created TEXT NOT NULL, risk_percent REAL NOT NULL, level TEXT NOT NULL, bmi REAL, profile TEXT)""")


init_db()


def _secret():
    path = ROOT / "data" / "api_secret.key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(os.urandom(32).hex())
    return path.read_text().strip().encode()


SECRET = _secret()


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)


def _sign(data):
    return base64.urlsafe_b64encode(hmac.new(SECRET, data, hashlib.sha256).digest()).decode().rstrip("=")


def make_token(username, days=7):
    body = base64.urlsafe_b64encode(json.dumps({"u": username, "exp": int(time.time()) + days * 86400}).encode()).decode().rstrip("=")
    return body + "." + _sign(body.encode())


def read_token(token):
    try:
        body, sig = token.split(".")
        if not hmac.compare_digest(sig, _sign(body.encode())):
            return None
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        return data["u"] if data["exp"] > time.time() else None
    except Exception:
        return None


bearer = HTTPBearer(auto_error=False)


def current_user(cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> str:
    user = read_token(cred.credentials) if cred else None
    if not user:
        raise HTTPException(status_code=401, detail="Please log in again.")
    return user


# ================================================================ request models
class Credentials(BaseModel):
    username: str
    password: str


class Profile(BaseModel):
    age_group: int = Field(..., ge=1, le=13, description="1 = 18-24 ... 13 = 80 or older")
    general_health: int = Field(..., ge=1, le=5, description="1 = Excellent ... 5 = Poor")
    height_cm: float = Field(..., ge=100, le=230)
    weight_kg: float = Field(..., ge=25, le=300)
    income_group: int = Field(..., ge=1, le=11)
    poor_health_days: int = Field(..., ge=0, le=30)
    exercise: bool
    difficulty_walking: bool
    heart_disease: bool
    scenario_bmi: Optional[float] = None
    scenario_exercise: Optional[bool] = None


# ================================================================ model helpers
def level_of(p):
    return "Low" if p < LOW_MAX else ("Moderate" if p < HIGH_MIN else "High")


def bmi_of(p):
    return round(p.weight_kg / ((p.height_cm / 100) ** 2), 1)


def frame(p, **over):
    v = {"_AGEG5YR": p.age_group, "GENHLTH": p.general_health, "_BMI5": bmi_of(p), "_MICHD": int(p.heart_disease),
         "DIFFWALK": int(p.difficulty_walking), "EXERANY2": int(p.exercise), "INCOME3": p.income_group, "PHYSHLTH": p.poor_health_days}
    v.update(over)
    return pd.DataFrame([v])[FEATURES]


def risk(p, **over):
    return float(MODEL.predict_proba(frame(p, **over))[0][1])


def explain(row):
    try:
        import shap
        global _EXPLAINER
        if "_EXPLAINER" not in globals():
            _EXPLAINER = shap.TreeExplainer(MODEL)
        sv = _EXPLAINER.shap_values(row)[0]
        items = [{"factor": NICE[f], "effect": round(float(x), 3), "direction": "raises" if x > 0 else "lowers"} for f, x in zip(FEATURES, sv)]
        return sorted(items, key=lambda d: abs(d["effect"]), reverse=True)
    except Exception:
        return []


def table(name):
    try:
        return pd.read_csv(REPORTS / name).round(3).to_dict("records")
    except Exception:
        return []


# ================================================================ public endpoints
@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0", "model_features": FEATURES}


@app.get("/meta")
def meta():
    return {"age_groups": AGE, "general_health": HEALTH, "income_groups": INCOME,
            "average_diabetes_rate_percent": round(BASE_RATE * 100, 1), "levels": {"low_below": LOW_MAX, "high_from": HIGH_MIN}}


@app.get("/insights")
def insights():
    return {"adults": int(len(DF)), "diabetes_percent": round(BASE_RATE * 100, 1),
            "age": {"labels": AGE, "rates": AGE_RATES}, "health": {"labels": HEALTH, "rates": HEALTH_RATES},
            "bmi": {"labels": BMI_LABELS, "rates": BMI_RATES}}


@app.get("/model-info")
def model_info():
    return {"comparison": table("model_comparison.csv"), "thresholds": table("threshold_table.csv"),
            "risk_levels": table("risk_band_table.csv"), "limitations": LIMITS}


@app.post("/register")
def register(c: Credentials):
    u = c.username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,20}", u):
        raise HTTPException(status_code=400, detail="Username must be 3 to 20 letters, digits or underscores.")
    if len(c.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")
    salt = os.urandom(16)
    try:
        with _db() as con:
            con.execute("INSERT INTO users (username, salt, pw_hash, created) VALUES (?,?,?,?)",
                        (u, salt, _hash(c.password, salt), datetime.now().isoformat(timespec="seconds")))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="That username is already taken.")
    return {"ok": True, "message": "Account created. You can log in now."}


@app.post("/login")
def login(c: Credentials):
    u = c.username.strip().lower()
    with _db() as con:
        row = con.execute("SELECT salt, pw_hash FROM users WHERE username=?", (u,)).fetchone()
    if row is None:
        _hash(c.password, b"0" * 16)
    if row is None or not hmac.compare_digest(_hash(c.password, row[0]), row[1]):
        raise HTTPException(status_code=401, detail="Wrong username or password.")
    return {"token": make_token(u), "username": u}


# ================================================================ endpoints that need a login
@app.get("/me")
def me(user: str = Depends(current_user)):
    return {"username": user}


@app.post("/predict")
def predict(p: Profile, user: str = Depends(current_user)):
    prob = risk(p)
    level = level_of(prob)
    out = {"bmi": bmi_of(p), "risk_percent": round(prob * 100, 1), "level": level, "advice": ADVICE[level],
           "average_adult_percent": round(BASE_RATE * 100, 1), "times_average": round(prob / BASE_RATE, 1),
           "factors": explain(frame(p)), "tips": TIPS, "disclaimer": "Screening aid only. Not a medical diagnosis."}
    if p.scenario_bmi is not None or p.scenario_exercise is not None:
        over = {}
        if p.scenario_bmi is not None:
            over["_BMI5"] = p.scenario_bmi
        if p.scenario_exercise is not None:
            over["EXERANY2"] = int(p.scenario_exercise)
        sp = risk(p, **over)
        out["scenario"] = {"risk_percent": round(sp * 100, 1), "level": level_of(sp), "change_points": round((sp - prob) * 100, 1)}
    return out


@app.post("/age-journey")
def age_journey(p: Profile, user: str = Depends(current_user)):
    you = [round(risk(p, _AGEG5YR=a) * 100, 1) for a in range(1, 14)]
    return {"labels": AGE, "you": you, "average": AGE_RATES}


@app.post("/bmi-curve")
def bmi_curve(p: Profile, user: str = Depends(current_user)):
    bmis = list(range(15, 51, 2))
    return {"bmi": bmis, "risk_percent": [round(risk(p, _BMI5=float(b)) * 100, 1) for b in bmis], "your_bmi": bmi_of(p)}


@app.post("/peers")
def peers(p: Profile, user: str = Depends(current_user)):
    key = (p.age_group, p.general_health)
    n, rate = (int(PEERS.loc[key, "count"]), float(PEERS.loc[key, "mean"])) if key in PEERS.index else (0, 0.0)
    return {"n": n, "peer_percent": round(rate * 100, 1), "overall_percent": round(BASE_RATE * 100, 1), "you_percent": round(risk(p) * 100, 1)}


@app.post("/history")
def save_history(p: Profile, user: str = Depends(current_user)):
    prob = risk(p)
    with _db() as con:
        con.execute("INSERT INTO history (username, created, risk_percent, level, bmi, profile) VALUES (?,?,?,?,?,?)",
                    (user, datetime.now().isoformat(timespec="seconds"), round(prob * 100, 1), level_of(prob), bmi_of(p),
                     json.dumps(p.dict() if hasattr(p, "dict") else {})))
    return {"saved": True, "risk_percent": round(prob * 100, 1), "level": level_of(prob)}


@app.get("/history")
def get_history(user: str = Depends(current_user)):
    with _db() as con:
        rows = con.execute("SELECT created, risk_percent, level, bmi FROM history WHERE username=? ORDER BY id", (user,)).fetchall()
    return {"items": [{"date": r[0], "risk_percent": r[1], "level": r[2], "bmi": r[3]} for r in rows]}


@app.delete("/history")
def clear_history(user: str = Depends(current_user)):
    with _db() as con:
        con.execute("DELETE FROM history WHERE username=?", (user,))
    return {"cleared": True}
