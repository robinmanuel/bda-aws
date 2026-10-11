#!/bin/bash
# ==============================================================================
# AWS EC2 User Data Bootstrap Script for Personal Diary Application
# Automatically executes on first boot of Amazon Linux 2023 / RHEL
# ==============================================================================

set -ex

echo "[+] Updating system packages..."
dnf update -y || yum update -y

echo "[+] Installing Python 3.11, git, and build tools..."
dnf install -y python3.11 python3.11-pip git || yum install -y python3 python3-pip git

# Create dedicated application directory
APP_DIR="/opt/diary-app"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

echo "[+] Cloning / Setting up Personal Diary repository..."
if [ -n "$REPO_URL" ]; then
    git clone "$REPO_URL" repo_temp
    cp -r repo_temp/app/* "$APP_DIR/"
    rm -rf repo_temp
else
    # Fallback: Clone default repository
    git clone https://github.com/robinmanuel/bda-aws.git repo_temp || true
    if [ -d "repo_temp/app" ]; then
        cp -r repo_temp/app/* "$APP_DIR/"
        rm -rf repo_temp
    fi
fi

# Ensure requirements file exists and install dependencies
cd "$APP_DIR"
python3.11 -m venv venv || python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install flask pymysql cryptography boto3 python-dotenv gunicorn werkzeug
fi

# Create production environment file
cat <<EOF > "$APP_DIR/.env"
DB_HOST=notes-db.c8dyocgsipef.us-east-1.rds.amazonaws.com
DB_PORT=3306
DB_USER=admin
DB_PASSWORD=SecurePass123!
DB_NAME=notes-db
S3_BUCKET_NAME=notes-bucket-assignment-116
AWS_REGION=us-east-1
PORT=80
EOF

# Ensure static/uploads exists
mkdir -p "$APP_DIR/static/uploads"
chmod -R 755 "$APP_DIR"

# Create systemd service for Gunicorn
echo "[+] Configuring systemd service..."
cat <<EOF > /etc/systemd/system/diary.service
[Unit]
Description=AWS Personal Diary 3-Tier Application
After=network.target

[Service]
User=root
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:80 --timeout 60 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload and start service
systemctl daemon-reload
systemctl enable diary.service
systemctl restart diary.service

echo "[+] Personal Diary application setup complete and running on port 80!"
