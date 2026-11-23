"""Simple login / logout for DiaScope (demo-level security).
Users and their saved results live in a small SQLite file: data/users.db
Passwords are never stored; only a salted PBKDF2 hash is kept.
"""
import hashlib
import hmac
import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "users.db"
ITERATIONS = 200_000


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
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            salt BLOB NOT NULL, pw_hash BLOB NOT NULL, created TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL, created TEXT NOT NULL,
            risk_percent REAL NOT NULL, level TEXT NOT NULL, bmi REAL, profile TEXT)""")


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)


def register(username, password):
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,20}", username):
        return False, "Username must be 3 to 20 letters, digits or underscores."
    if len(password) < 6:
        return False, "Password must be at least 6 characters."
    salt = os.urandom(16)
    try:
        with _db() as con:
            con.execute("INSERT INTO users (username, salt, pw_hash, created) VALUES (?,?,?,?)",
                        (username, salt, _hash(password, salt), datetime.now().isoformat(timespec="seconds")))
    except sqlite3.IntegrityError:
        return False, "That username is already taken."
    return True, "Account created. You can log in now."


def verify(username, password):
    username = username.strip().lower()
    with _db() as con:
        row = con.execute("SELECT salt, pw_hash FROM users WHERE username=?", (username,)).fetchone()
    if row is None:
        _hash(password, b"0" * 16)  # keep timing similar for unknown users
        return False
    return hmac.compare_digest(_hash(password, row[0]), row[1])


def add_history(username, risk_percent, level, bmi, profile):
    with _db() as con:
        con.execute("INSERT INTO history (username, created, risk_percent, level, bmi, profile) VALUES (?,?,?,?,?,?)",
                    (username, datetime.now().isoformat(timespec="seconds"), float(risk_percent), level, float(bmi),
                     json.dumps(profile)))


def get_history(username):
    with _db() as con:
        rows = con.execute("SELECT created, risk_percent, level, bmi FROM history WHERE username=? ORDER BY id",
                           (username,)).fetchall()
    return pd.DataFrame(rows, columns=["Date", "Risk %", "Level", "BMI"])


def clear_history(username):
    with _db() as con:
        con.execute("DELETE FROM history WHERE username=?", (username,))


# ---------------------------------------------------------------- Streamlit pages
def require_login():
    """Show the login / register page until the user signs in. Returns the username."""
    init_db()
    if st.session_state.get("user"):
        return st.session_state["user"]

    st.markdown("""
    <div class="hero">
      <div class="hero-tag">SECURE ACCESS</div>
      <div class="hero-title">DiaScope</div>
      <div class="hero-sub">Log in to check your diabetes risk and keep a history of your results.</div>
    </div>""", unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.6, 1])
    with mid:
        tab_login, tab_new = st.tabs(["Log in", "Create account"])
        with tab_login:
            with st.form("login_form"):
                u = st.text_input("Username")
                p = st.text_input("Password", type="password")
                go = st.form_submit_button("Log in")
            if go:
                if verify(u, p):
                    st.session_state["user"] = u.strip().lower()
                    st.rerun()
                else:
                    st.error("Wrong username or password.")
        with tab_new:
            with st.form("register_form"):
                u2 = st.text_input("Choose a username")
                p2 = st.text_input("Choose a password", type="password")
                p3 = st.text_input("Repeat the password", type="password")
                go2 = st.form_submit_button("Create account")
            if go2:
                if p2 != p3:
                    st.error("The two passwords do not match.")
                else:
                    ok, msg = register(u2, p2)
                    (st.success if ok else st.error)(msg)
        st.caption("Demo-level security: passwords are stored only as salted hashes, and no personal health data leaves this computer.")
    st.stop()


def logout():
    st.session_state.pop("user", None)
    st.rerun()
