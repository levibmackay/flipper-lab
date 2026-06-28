# Flipper Lab

An intentionally vulnerable web server built for pen testing practice with a Flipper Zero and Raspberry Pi. The server runs on the Pi; you attack it from your Mac over the network or from the Flipper over USB.

> **For authorized testing only. Run this on hardware you own.**

---

## Setup

```bash
git clone https://github.com/levibmackay/flipper-lab.git
cd flipper-lab
pip install -r requirements.txt
```

### Start everything (server + live dashboard in tmux)

```bash
bash start.sh
```

This opens two tmux panes side by side:
- **Left** — the vulnerable Flask server on port 5000
- **Right** — a live Rich dashboard showing every request and flagging attacks in real time

You can SSH into the Pi from your Mac and run `bash start.sh` to see both panes in your terminal.

### Or start them separately

```bash
# Terminal 1 — server
python3 server/app.py

# Terminal 2 — dashboard
python3 monitor/dashboard.py
```

---

## Vulnerabilities

| # | Type | Where |
|---|------|--------|
| 1 | SQL Injection | `POST /login` — username/password fields |
| 2 | Command Injection | `GET /tools/ping?host=` |
| 3 | Directory Traversal | `GET /files?file=` |
| 4 | IDOR | `GET /api/user/<id>` — no ownership check |
| 5 | Weak credentials | `/admin` — `admin / password123` |

### Example attacks (from your Mac or browser)

**SQL Injection — bypass login**
```
Username: ' OR '1'='1' --
Password: anything
```

**Command Injection — run arbitrary commands**
```
http://<pi-ip>:5000/tools/ping?host=127.0.0.1;id
http://<pi-ip>:5000/tools/ping?host=127.0.0.1;cat /etc/passwd
```

**Directory Traversal — read files outside the web root**
```
http://<pi-ip>:5000/files?file=../flag.txt
http://<pi-ip>:5000/files?file=../../etc/passwd
```

**IDOR — read any user's profile**
```
http://<pi-ip>:5000/api/user/1
http://<pi-ip>:5000/api/user/2
```

**Admin panel — default creds**
```
http://<pi-ip>:5000/admin
Login as admin / password123 to see the flag
```

---

## Flipper Zero — Bad USB Payloads

Plug your Flipper into the Pi's USB port. Load a payload from `payloads/` onto the Flipper's SD card under `badusb/`.

| Payload | What it does |
|---------|-------------|
| `exfil_flag.txt` | Opens a terminal and cats `flag.txt` to the screen |
| `reverse_shell.txt` | Drops a bash reverse shell back to your machine (edit IP first) |
| `add_backdoor_user.txt` | Adds a user `flipper / flipper123` via sudo |

**To load on Flipper:**
1. Copy the `.txt` file to `/SD/badusb/` on your Flipper's SD card
2. On the Flipper: `Bad USB → <payload name> → Run`
3. The Flipper types the payload as if it were a keyboard

---

## Watching from SSH

SSH into the Pi from your Mac, then run `bash start.sh`. The tmux session splits the screen — server logs on the left, the attack dashboard on the right. Every request is logged and attacks are highlighted in red as they come in.

```bash
ssh pi@<pi-ip>
cd flipper-lab
bash start.sh
```

---

## File layout

```
flipper-lab/
├── server/
│   ├── app.py          # Vulnerable Flask server
│   ├── flag.txt        # Target for Bad USB exfil payloads
│   ├── static/         # Served files (traversal target)
│   └── templates/      # HTML pages
├── monitor/
│   └── dashboard.py    # Rich live attack dashboard
├── payloads/           # Flipper Zero DuckyScript Bad USB payloads
├── start.sh            # Launches both server and dashboard in tmux
└── requirements.txt
```
