# ARS Consignment System — Deployment Guide
## Server: Ubuntu 22.04 VPS (Hetzner / DigitalOcean)

---

## STEP 1: Initial Server Setup

```bash
# SSH into your server
ssh root@YOUR_SERVER_IP

# Update packages
apt update && apt upgrade -y

# Create app user
adduser arsapp
usermod -aG sudo arsapp
su - arsapp
```

---

## STEP 2: Install Dependencies

```bash
# Python 3.11+
sudo apt install python3 python3-pip python3-venv -y

# WeasyPrint system dependencies
sudo apt install -y \
  libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
  libgdk-pixbuf2.0-0 libffi-dev shared-mime-info \
  libcairo2 libcairo2-dev python3-dev gcc

# Nginx
sudo apt install nginx -y
```

---

## STEP 3: Deploy Application

```bash
# Create app directory
mkdir -p /home/arsapp/ars_consignment
cd /home/arsapp/ars_consignment

# Upload your project files here (via scp or git)
# scp -r ./ars_consignment/* arsapp@YOUR_IP:/home/arsapp/ars_consignment/

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python packages
pip install -r requirements.txt

# Create generated PDFs directory
mkdir -p generated_pdfs

# Test run
python main.py
# Visit http://YOUR_IP:8000 — should see login page
# Default login: admin / admin123
# CHANGE THIS PASSWORD IMMEDIATELY via User Management
```

---

## STEP 4: Run as a Service (systemd)

```bash
sudo nano /etc/systemd/system/ars.service
```

Paste:
```ini
[Unit]
Description=ARS Consignment System
After=network.target

[Service]
User=arsapp
WorkingDirectory=/home/arsapp/ars_consignment
ExecStart=/home/arsapp/ars_consignment/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable ars
sudo systemctl start ars
sudo systemctl status ars
```

---

## STEP 5: Nginx Reverse Proxy

```bash
sudo nano /etc/nginx/sites-available/ars
```

Paste (replace YOUR_DOMAIN):
```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    client_max_body_size 10M;

    location /static/ {
        alias /home/arsapp/ars_consignment/static/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/ars /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## STEP 6: SSL Certificate (HTTPS) — Recommended

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d YOUR_DOMAIN
# Follow prompts — auto-renews every 90 days
```

---

## STEP 7: First Login & Configuration

1. Visit https://YOUR_DOMAIN
2. Login: `admin` / `admin123`
3. **Immediately go to Admin → Users → change admin password**
4. Go to Admin → Settings → configure SMTP (Gmail recommended):
   - Host: `smtp.gmail.com`
   - Port: `587`
   - Username: your Gmail address
   - Password: Gmail App Password (not your regular password)
   - Get App Password at: https://myaccount.google.com/apppasswords
5. Add staff users via Admin → Users

---

## IMPORTANT SECURITY NOTES

- Change `ARS-SECRET-CHANGE-IN-PROD-2025` in `main.py` to a long random string
- Change default admin password immediately
- Keep your VPS firewall configured: only ports 22, 80, 443 open
- Regular SQLite backups: `cp database/ars.db database/ars_backup_$(date +%Y%m%d).db`

---

## BACKUP COMMAND (run via cron daily)

```bash
# crontab -e
0 2 * * * cp /home/arsapp/ars_consignment/database/ars.db /home/arsapp/backups/ars_$(date +\%Y\%m\%d).db
```

---

## PROJECT STRUCTURE

```
ars_consignment/
├── main.py                  # FastAPI app entry point
├── requirements.txt         # Python dependencies
├── database/
│   ├── db.py               # SQLite models & helpers
│   └── ars.db              # Database file (auto-created)
├── routers/
│   ├── auth.py             # Login / logout
│   ├── consignment.py      # Form, save, view entries
│   └── admin.py            # User management, settings
├── services/
│   ├── pdf_service.py      # WeasyPrint PDF generation
│   └── email_service.py    # SMTP email dispatch
├── templates/              # Jinja2 HTML templates
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── consignment_form.html
│   ├── view_consignment.html
│   ├── admin_users.html
│   └── admin_settings.html
├── static/
│   ├── css/main.css
│   └── js/main.js
└── generated_pdfs/         # PDF output folder (auto-created)
```
