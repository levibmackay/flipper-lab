#!/usr/bin/env python3
"""Intentionally vulnerable Flask server — for authorized pen testing only."""

import os
import sqlite3
import subprocess
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template, session, redirect, url_for

app = Flask(__name__)
app.secret_key = "supersecret123"

DB_PATH   = os.path.join(os.path.dirname(__file__), "users.db")
FLAG_PATH = os.path.join(os.path.dirname(__file__), "flag.txt")
# When running in Docker this resolves to /app/requests.log, which is volume-mounted
LOG_PATH  = "/app/requests.log"

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(message)s")

def log_request(extra=""):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} | {request.remote_addr} | {request.method} {request.path}"
    if request.args:
        line += f" | PARAMS: {dict(request.args)}"
    if request.form:
        line += f" | FORM: {dict(request.form)}"
    if extra:
        line += f" | {extra}"
    logging.info(line)

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT,
            role TEXT DEFAULT 'user'
        )
    """)
    cur.execute("DELETE FROM users")
    cur.executemany("INSERT INTO users VALUES (?,?,?,?)", [
        (1, "admin",   "password123", "admin"),
        (2, "alice",   "alice2024",   "user"),
        (3, "bob",     "hunter2",     "user"),
        (4, "charlie", "letmein",     "user"),
    ])
    con.commit()
    con.close()

def get_db():
    return sqlite3.connect(DB_PATH)

@app.route("/")
def index():
    log_request()
    return render_template("index.html", user=session.get("user"))

# VULN 1: SQL Injection
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        log_request(f"LOGIN ATTEMPT: {username}")
        con = get_db()
        cur = con.cursor()
        query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
        try:
            cur.execute(query)
            row = cur.fetchone()
        except Exception as e:
            row = None
            error = f"DB error: {e}"
        con.close()
        if row:
            session["user"] = row[1]
            session["role"] = row[3]
            log_request(f"LOGIN SUCCESS: {row[1]} role={row[3]}")
            return redirect(url_for("dashboard"))
        else:
            error = "Invalid credentials"
            log_request("LOGIN FAILED")
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    log_request()
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["user"], role=session.get("role"))

# VULN 2: Command Injection
@app.route("/tools/ping")
def ping():
    host = request.args.get("host", "")
    log_request(f"PING: {host}")
    if not host:
        return render_template("ping.html", result=None)
    try:
        result = subprocess.check_output(
            f"ping -c 2 {host}", shell=True, stderr=subprocess.STDOUT, timeout=5, text=True
        )
    except subprocess.TimeoutExpired:
        result = "Timed out"
    except subprocess.CalledProcessError as e:
        result = e.output
    return render_template("ping.html", result=result, host=host)

# VULN 3: Directory Traversal
@app.route("/files")
def files():
    filename = request.args.get("file", "")
    log_request(f"FILE: {filename}")
    if not filename:
        return render_template("files.html", content=None, filename=None)
    base = os.path.join(os.path.dirname(__file__), "static")
    path = os.path.join(base, filename)
    try:
        with open(path) as f:
            content = f.read()
    except Exception as e:
        content = f"Error: {e}"
    return render_template("files.html", content=content, filename=filename)

# VULN 4: IDOR
@app.route("/api/user/<int:user_id>")
def user_profile(user_id):
    log_request(f"PROFILE LOOKUP: id={user_id}")
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT id, username, role FROM users WHERE id=?", (user_id,))
    row = cur.fetchone()
    con.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    return jsonify({"id": row[0], "username": row[1], "role": row[2]})

# VULN 5: Exposed admin panel (admin / password123)
@app.route("/admin")
def admin():
    log_request()
    if session.get("role") != "admin":
        return render_template("admin.html", locked=True)
    try:
        with open(FLAG_PATH) as f:
            flag = f.read().strip()
    except Exception:
        flag = "FLAG{file_not_found}"
    return render_template("admin.html", locked=False, flag=flag)

if __name__ == "__main__":
    init_db()
    print("  Vulnerable server running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
