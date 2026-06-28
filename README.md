# Flipper Lab

An intentionally vulnerable web server for pen testing practice with a Flipper Zero and Raspberry Pi.

**Everything runs inside Docker** — command injection, directory traversal, and Bad USB payloads all hit the container's isolated environment, not your Pi's real OS. Wipe and start over in one command.

> For authorized testing on hardware you own only.

---

## Quick start

```bash
git clone https://github.com/levibmackay/flipper-lab.git
cd flipper-lab
bash start.sh
```

This builds the Docker container, starts the server on port 5000, and opens the live attack dashboard in your terminal. SSH in from your Mac and run it there — you'll see every hit in real time.

### Wipe and start over

```bash
bash start.sh wipe
```

Destroys the container, clears all state and logs, then rebuilds from scratch. Takes about 10 seconds.

---

## Vulnerabilities

| # | Type | Endpoint |
|---|------|----------|
| 1 | SQL Injection | `POST /login` — username/password fields |
| 2 | Command Injection | `GET /tools/ping?host=` |
| 3 | Directory Traversal | `GET /files?file=` |
| 4 | IDOR | `GET /api/user/<id>` — no ownership check |
| 5 | Weak credentials | `/admin` — `admin / password123` |

### Attacks to try from your Mac browser

**SQL Injection — bypass login entirely**
```
Username: ' OR '1'='1' --
Password: anything
```

**Command Injection — run shell commands inside the container**
```
http://<pi-ip>:5000/tools/ping?host=127.0.0.1;id
http://<pi-ip>:5000/tools/ping?host=127.0.0.1;cat /etc/passwd
```

**Directory Traversal — read files outside the web root**
```
http://<pi-ip>:5000/files?file=../flag.txt
http://<pi-ip>:5000/files?file=../../../etc/passwd
```

**IDOR — access any user's data**
```
http://<pi-ip>:5000/api/user/1
http://<pi-ip>:5000/api/user/2
```

---

## Flipper Zero — Bad USB Payloads

The payloads use `curl` to attack the server through its web vulnerabilities.
This keeps everything inside Docker — nothing touches your Pi's real OS.

### How to load

1. Copy a `.txt` file from `payloads/` to `/SD/badusb/` on your Flipper's SD card
2. Plug Flipper into the Pi's USB port
3. On the Flipper: **Bad USB → `<payload name>` → Run**
4. Watch the dashboard — the attack shows up in red

### Payloads

| File | What it does |
|------|-------------|
| `exfil_flag.txt` | Reads `flag.txt` via directory traversal |
| `sqli_bypass.txt` | Bypasses login with SQL injection, then hits `/admin` |
| `cmd_injection.txt` | Runs `id` and `whoami` inside the container via the ping tool |
| `traversal_passwd.txt` | Reads the container's `/etc/passwd` via traversal |

---

## Why Docker?

Without Docker, Bad USB payloads that run system commands would affect your actual Pi — creating users, dropping shells, etc. Inside Docker:

- The container has its own filesystem, users, and network namespace
- `cat /etc/passwd` reads the container's passwd file, not your Pi's
- `wipe` blows away the container completely and starts fresh
- Your Pi's OS is never touched

---

## Remote Flipper control (from SSH)

Plug the Flipper into the Pi's USB port. You can then control it entirely from your SSH session — upload payloads, list what's on the SD card, and trigger Bad USB runs without touching the Flipper.

```bash
cd controller
pip install -r requirements.txt

# Check Flipper is detected
ls /dev/ttyACM0

# Show device info
python3 flipper_ctl.py info

# List payloads already on the Flipper SD card
python3 flipper_ctl.py list

# Upload a payload from this repo to the Flipper
python3 flipper_ctl.py upload ../payloads/exfil_flag.txt

# Run a payload remotely — opens Bad USB app and presses OK
python3 flipper_ctl.py run exfil_flag.txt

# Clean up
python3 flipper_ctl.py delete exfil_flag.txt
```

`run` works by opening the Bad USB app on the Flipper over serial, then sending virtual button presses to navigate the file picker and press OK — all without touching the device.

---

## File layout

```
flipper-lab/
├── server/
│   ├── app.py              # Vulnerable Flask server
│   ├── flag.txt            # Target for exfil payloads
│   ├── static/             # File browser root (traversal target)
│   └── templates/          # HTML pages
├── monitor/
│   └── dashboard.py        # Rich live attack dashboard
├── controller/
│   ├── flipper_ctl.py      # Remote Flipper control CLI (upload, list, run, delete)
│   └── requirements.txt
├── payloads/               # Flipper Zero DuckyScript Bad USB payloads
├── Dockerfile
├── docker-compose.yml
├── start.sh                # Start everything / wipe
└── requirements.txt        # Dashboard dependencies (Rich)
```
