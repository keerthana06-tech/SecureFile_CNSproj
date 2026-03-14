import os
import hashlib
import sqlite3
import shutil
import random
import string
import json
from datetime import datetime, timedelta
from functools import wraps

import bcrypt
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, send_file, abort)
from cryptography.fernet import Fernet
from werkzeug.utils import secure_filename

# ── App Setup ────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.urandom(32)
app.permanent_session_lifetime = timedelta(hours=2)

BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
VAULT_FOLDER  = os.path.join(BASE_DIR, "static", "vault")
DB_PATH       = os.path.join(BASE_DIR, "database.db")
KEY_FILE      = os.path.join(BASE_DIR, "vault.key")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VAULT_FOLDER,  exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "txt", "pdf",
                       "doc", "docx", "mp4", "avi", "mkv", "zip"}

# ── Encryption Key ────────────────────────────────────────────────────────────
def get_fernet():
    if not os.path.exists(KEY_FILE):
        key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(key)
    with open(KEY_FILE, "rb") as f:
        return Fernet(f.read())

fernet = get_fernet()

# ── Database ──────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                username      TEXT    UNIQUE NOT NULL,
                email         TEXT    UNIQUE NOT NULL,
                password_hash TEXT    NOT NULL,
                created_at    TEXT    DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                filename    TEXT    NOT NULL,
                file_hash   TEXT    NOT NULL,
                file_type   TEXT,
                upload_date TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS vault (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL,
                folder_name      TEXT    NOT NULL DEFAULT 'Root',
                original_name    TEXT    NOT NULL,
                stored_name      TEXT    NOT NULL,
                file_hash        TEXT,
                encrypted_status INTEGER DEFAULT 1,
                upload_date      TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS folders (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                folder_name TEXT    NOT NULL,
                created_at  TEXT    DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)

init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def generate_otp():
    return "".join(random.choices(string.digits, k=6))

# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("dashboard") if "user_id" in session else url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        remember = request.form.get("remember") == "on"

        with get_db() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username=?", (username,)
            ).fetchone()

        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            session.permanent = remember
            session["user_id"]  = user["id"]
            session["username"] = user["username"]
            flash("Welcome back, " + user["username"] + "!", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email    = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("signup.html")

        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            with get_db() as conn:
                conn.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?,?,?)",
                    (username, email, pw_hash)
                )
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "error")
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route("/dashboard")
@login_required
def dashboard():
    with get_db() as conn:
        file_count  = conn.execute(
            "SELECT COUNT(*) FROM files WHERE user_id=?", (session["user_id"],)
        ).fetchone()[0]
        vault_count = conn.execute(
            "SELECT COUNT(*) FROM vault WHERE user_id=?", (session["user_id"],)
        ).fetchone()[0]
    return render_template("dashboard.html",
                           username=session["username"],
                           file_count=file_count,
                           vault_count=vault_count)

# ── File Detection ─────────────────────────────────────────────────────────────
@app.route("/detect", methods=["GET", "POST"])
@login_required
def detect():
    with get_db() as conn:
        history = conn.execute(
            "SELECT * FROM files WHERE user_id=? ORDER BY upload_date DESC LIMIT 20",
            (session["user_id"],)
        ).fetchall()
    return render_template("detect.html", history=history)

@app.route("/upload_original", methods=["POST"])
@login_required
def upload_original():
    f = request.files.get("file")
    if not f or not allowed_file(f.filename):
        return jsonify({"error": "Invalid file"}), 400

    filename = secure_filename(f.filename)
    uid_dir  = os.path.join(UPLOAD_FOLDER, str(session["user_id"]))
    os.makedirs(uid_dir, exist_ok=True)
    path = os.path.join(uid_dir, "original_" + filename)
    f.save(path)
    file_hash = sha256_file(path)
    ext = filename.rsplit(".", 1)[1].lower()

    with get_db() as conn:
        conn.execute(
            "INSERT INTO files (user_id, filename, file_hash, file_type) VALUES (?,?,?,?)",
            (session["user_id"], filename, file_hash, ext)
        )

    session["original_path"] = path
    session["original_hash"] = file_hash
    session["original_name"] = filename
    session["original_ext"]  = ext

    return jsonify({
        "filename": filename,
        "hash":     file_hash,
        "type":     ext,
        "url":      "/" + path.replace(BASE_DIR + "/", "").replace("\\", "/")
    })

@app.route("/compare_files", methods=["POST"])
@login_required
def compare_files():
    orig_path = session.get("original_path")
    if not orig_path or not os.path.exists(orig_path):
        return jsonify({"error": "Upload original file first"}), 400

    f = request.files.get("file")
    if not f or not allowed_file(f.filename):
        return jsonify({"error": "Invalid comparison file"}), 400

    filename = secure_filename(f.filename)
    uid_dir  = os.path.join(UPLOAD_FOLDER, str(session["user_id"]))
    cmp_path = os.path.join(uid_dir, "compare_" + filename)
    f.save(cmp_path)

    cmp_hash   = sha256_file(cmp_path)
    orig_hash  = session.get("original_hash", "")
    hashes_match = (cmp_hash == orig_hash)
    ext = session.get("original_ext", "txt")

    result = {
        "original_hash":   orig_hash,
        "compare_hash":    cmp_hash,
        "hashes_match":    hashes_match,
        "tampered":        not hashes_match,
        "original_url":    "/" + orig_path.replace(BASE_DIR + "/", "").replace("\\", "/"),
        "compare_url":     "/" + cmp_path.replace(BASE_DIR + "/", "").replace("\\", "/"),
        "diff_url":        None,
        "differences":     [],
        "file_type":       ext,
    }

    if not hashes_match:
        # Text comparison
        if ext == "txt":
            try:
                with open(orig_path, "r", errors="ignore") as o, \
                     open(cmp_path,  "r", errors="ignore") as c:
                    orig_lines = o.readlines()
                    cmp_lines  = c.readlines()
                import difflib
                diff = list(difflib.unified_diff(orig_lines, cmp_lines,
                                                 fromfile="original", tofile="modified"))
                result["differences"] = diff[:100]
            except Exception:
                pass

        # Image comparison
        elif ext in ("png", "jpg", "jpeg", "gif"):
            try:
                import cv2
                import numpy as np
                img1 = cv2.imread(orig_path)
                img2 = cv2.imread(cmp_path)
                if img1 is not None and img2 is not None:
                    h = min(img1.shape[0], img2.shape[0])
                    w = min(img1.shape[1], img2.shape[1])
                    img1r = cv2.resize(img1, (w, h))
                    img2r = cv2.resize(img2, (w, h))
                    diff  = cv2.absdiff(img1r, img2r)
                    gray  = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
                    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL,
                                                   cv2.CHAIN_APPROX_SIMPLE)
                    output = img2r.copy()
                    for cnt in contours:
                        if cv2.contourArea(cnt) > 50:
                            x, y, bw, bh = cv2.boundingRect(cnt)
                            cv2.rectangle(output, (x, y), (x+bw, y+bh), (0, 0, 255), 2)
                    diff_name = "diff_" + filename
                    diff_path = os.path.join(uid_dir, diff_name)
                    cv2.imwrite(diff_path, output)
                    result["diff_url"] = "/" + diff_path.replace(BASE_DIR + "/", "").replace("\\", "/")
            except Exception as e:
                result["diff_error"] = str(e)

    return jsonify(result)

@app.route("/delete_file/<int:file_id>", methods=["POST"])
@login_required
def delete_file(file_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM files WHERE id=? AND user_id=?",
            (file_id, session["user_id"])
        ).fetchone()
        if row:
            conn.execute("DELETE FROM files WHERE id=?", (file_id,))
    return jsonify({"success": True})

# ── Secure Vault ──────────────────────────────────────────────────────────────
@app.route("/vault")
@login_required
def vault():
    with get_db() as conn:
        folders = conn.execute(
            "SELECT * FROM folders WHERE user_id=? ORDER BY folder_name",
            (session["user_id"],)
        ).fetchall()
        files = conn.execute(
            "SELECT * FROM vault WHERE user_id=? ORDER BY upload_date DESC",
            (session["user_id"],)
        ).fetchall()
    return render_template("vault.html", folders=folders, files=files)

@app.route("/vault/create_folder", methods=["POST"])
@login_required
def create_folder():
    name = request.form.get("folder_name", "").strip()
    if not name:
        return jsonify({"error": "Folder name required"}), 400
    with get_db() as conn:
        conn.execute(
            "INSERT INTO folders (user_id, folder_name) VALUES (?,?)",
            (session["user_id"], name)
        )
    flash("Folder created.", "success")
    return redirect(url_for("vault"))

@app.route("/vault/delete_folder/<int:folder_id>", methods=["POST"])
@login_required
def delete_folder(folder_id):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM folders WHERE id=? AND user_id=?",
            (folder_id, session["user_id"])
        )
    flash("Folder deleted.", "info")
    return redirect(url_for("vault"))

@app.route("/vault/upload", methods=["POST"])
@login_required
def vault_upload():
    f = request.files.get("file")
    folder = request.form.get("folder_name", "Root")
    if not f or not allowed_file(f.filename):
        flash("Invalid file.", "error")
        return redirect(url_for("vault"))

    original_name = secure_filename(f.filename)
    uid_dir = os.path.join(VAULT_FOLDER, str(session["user_id"]))
    os.makedirs(uid_dir, exist_ok=True)

    # Save temporarily to hash
    tmp_path = os.path.join(uid_dir, "tmp_" + original_name)
    f.save(tmp_path)
    file_hash = sha256_file(tmp_path)

    # Encrypt
    with open(tmp_path, "rb") as raw:
        encrypted = fernet.encrypt(raw.read())
    stored_name = hashlib.md5(file_hash.encode()).hexdigest() + ".enc"
    enc_path = os.path.join(uid_dir, stored_name)
    with open(enc_path, "wb") as ef:
        ef.write(encrypted)
    os.remove(tmp_path)

    with get_db() as conn:
        conn.execute(
            """INSERT INTO vault
               (user_id, folder_name, original_name, stored_name, file_hash)
               VALUES (?,?,?,?,?)""",
            (session["user_id"], folder, original_name, stored_name, file_hash)
        )
    flash("File uploaded securely to vault.", "success")
    return redirect(url_for("vault"))

@app.route("/vault/verify_otp", methods=["POST"])
@login_required
def verify_otp():
    """Step 1: verify password → generate OTP."""
    data     = request.get_json()
    password = data.get("password", "")
    file_id  = data.get("file_id")

    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE id=?", (session["user_id"],)
        ).fetchone()

    if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return jsonify({"success": False, "message": "Wrong password"}), 401

    otp = generate_otp()
    session["vault_otp"]     = otp
    session["vault_file_id"] = file_id
    session["otp_expires"]   = (datetime.utcnow() + timedelta(minutes=5)).isoformat()

    # In production send via email/SMS; here we return it for demo
    return jsonify({"success": True, "otp": otp,
                    "message": "OTP generated (demo: shown here)"})

@app.route("/vault/download/<int:file_id>", methods=["POST"])
@login_required
def vault_download(file_id):
    """Step 2: verify OTP → decrypt → send file."""
    data = request.get_json()
    otp  = data.get("otp", "")

    if (session.get("vault_otp") != otp or
            session.get("vault_file_id") != file_id):
        return jsonify({"success": False, "message": "Invalid OTP"}), 401

    expires = session.get("otp_expires")
    if expires and datetime.utcnow() > datetime.fromisoformat(expires):
        return jsonify({"success": False, "message": "OTP expired"}), 401

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM vault WHERE id=? AND user_id=?",
            (file_id, session["user_id"])
        ).fetchone()

    if not row:
        return jsonify({"success": False, "message": "File not found"}), 404

    uid_dir  = os.path.join(VAULT_FOLDER, str(session["user_id"]))
    enc_path = os.path.join(uid_dir, row["stored_name"])
    with open(enc_path, "rb") as ef:
        decrypted = fernet.decrypt(ef.read())

    tmp_path = os.path.join(uid_dir, "dl_" + row["original_name"])
    with open(tmp_path, "wb") as tf:
        tf.write(decrypted)

    # Clear OTP
    session.pop("vault_otp", None)
    session.pop("vault_file_id", None)

    response = send_file(tmp_path, as_attachment=True,
                         download_name=row["original_name"])
    return response

@app.route("/vault/delete/<int:file_id>", methods=["POST"])
@login_required
def vault_delete(file_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM vault WHERE id=? AND user_id=?",
            (file_id, session["user_id"])
        ).fetchone()
        if row:
            uid_dir  = os.path.join(VAULT_FOLDER, str(session["user_id"]))
            enc_path = os.path.join(uid_dir, row["stored_name"])
            if os.path.exists(enc_path):
                os.remove(enc_path)
            conn.execute("DELETE FROM vault WHERE id=?", (file_id,))
    flash("File deleted from vault.", "info")
    return redirect(url_for("vault"))

# ── Guidelines ────────────────────────────────────────────────────────────────
@app.route("/guidelines")
@login_required
def guidelines():
    return render_template("guidelines.html")

# ── Profile ───────────────────────────────────────────────────────────────────
@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    with get_db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE id=?", (session["user_id"],)
        ).fetchone()
        file_count  = conn.execute(
            "SELECT COUNT(*) FROM files WHERE user_id=?", (session["user_id"],)
        ).fetchone()[0]
        vault_count = conn.execute(
            "SELECT COUNT(*) FROM vault WHERE user_id=?", (session["user_id"],)
        ).fetchone()[0]

    if request.method == "POST":
        current_pw  = request.form.get("current_password", "")
        new_pw      = request.form.get("new_password", "")
        confirm_pw  = request.form.get("confirm_password", "")

        if not bcrypt.checkpw(current_pw.encode(), user["password_hash"].encode()):
            flash("Current password is incorrect.", "error")
        elif new_pw != confirm_pw:
            flash("New passwords do not match.", "error")
        elif len(new_pw) < 6:
            flash("Password must be at least 6 characters.", "error")
        else:
            new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt()).decode()
            with get_db() as conn:
                conn.execute(
                    "UPDATE users SET password_hash=? WHERE id=?",
                    (new_hash, session["user_id"])
                )
            flash("Password updated successfully.", "success")

    return render_template("profile.html", user=user,
                           file_count=file_count, vault_count=vault_count)

if __name__ == "__main__":
    app.run(debug=True)
