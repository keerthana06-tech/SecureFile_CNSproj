# SecureVault — Advanced File Integrity & Secure Storage

A cybersecurity-themed web application built with Python Flask featuring:
- SHA-256 file tamper detection with visual diff
- AES-256 encrypted file vault
- Double verification (password + OTP) for file access
- Voice-assisted guidelines
- Animated cyber-themed UI

---

## Project Structure

```
securevault/
├── app.py                   ← Main Flask backend
├── requirements.txt         ← Python dependencies
├── database.db              ← Auto-created on first run
├── vault.key                ← Auto-created encryption key
├── static/
│   ├── css/
│   │   ├── style.css        ← Dashboard/inner pages styles
│   │   └── auth.css         ← Login/signup styles
│   ├── js/
│   │   ├── main.js          ← Sidebar + toast helpers
│   │   ├── auth.js          ← Animated particle background
│   │   ├── detect.js        ← File comparison logic
│   │   ├── vault.js         ← 2FA download flow
│   │   └── guidelines.js   ← Web Speech API voice assistant
│   ├── uploads/             ← Auto-created for tamper detection files
│   └── vault/               ← Auto-created for encrypted vault files
└── templates/
    ├── base.html            ← Sidebar + flash messages layout
    ├── login.html
    ├── signup.html
    ├── dashboard.html
    ├── detect.html
    ├── vault.html
    ├── guidelines.html
    └── profile.html
```

---

## Setup Instructions (VS Code)

### Step 1 — Open the project folder
```
File → Open Folder → select securevault/
```

### Step 2 — Create a virtual environment
Open Terminal in VS Code (Ctrl + `) and run:
```bash
python -m venv venv
```

### Step 3 — Activate the virtual environment
**Windows:**
```bash
venv\Scripts\activate
```
**Mac/Linux:**
```bash
source venv/bin/activate
```

### Step 4 — Install dependencies
```bash
pip install -r requirements.txt
```
> Note: If opencv install fails, try: `pip install opencv-python-headless`
> If PyMuPDF fails, try: `pip install pymupdf`

### Step 5 — Run the application
```bash
python app.py
```

### Step 6 — Open in browser
```
http://127.0.0.1:5000
```

---

## Features

| Feature | Description |
|---|---|
| Registration/Login | bcrypt hashed passwords, session management |
| Tamper Detection | SHA-256 hashing, image diff with OpenCV bounding boxes, text diff |
| Secure Vault | AES-256 Fernet encryption, folder organization |
| Double Verification | Password check → OTP generation → decrypt & download |
| Voice Assistant | Web Speech API reads guidelines aloud |
| Scan History | Track all previously scanned files |
| Profile | Change password, view stats |

---

## Tech Stack

- **Backend:** Python Flask
- **Database:** SQLite (auto-created)
- **Encryption:** cryptography (Fernet / AES-256)
- **Hashing:** hashlib SHA-256
- **Password:** bcrypt
- **Image Diff:** OpenCV
- **Frontend:** HTML5, CSS3, Vanilla JS
- **Icons:** FontAwesome 6
- **Fonts:** Rajdhani, Exo 2, Share Tech Mono (Google Fonts)

---

## Notes

- The OTP is displayed on-screen for demo purposes. In production, integrate an email/SMS service.
- `vault.key` is auto-generated on first run. **Back it up** — losing it means losing access to all encrypted vault files.
- `database.db` is auto-created on first run.
- The `uploads/` and `vault/` folders are auto-created inside `static/`.
