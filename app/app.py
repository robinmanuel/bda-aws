import os
import uuid
import time
import urllib.request
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
import pymysql
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

from config import Config

app = Flask(__name__)
app.config.from_object(Config)

# Ensure local upload directory exists if needed
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# -------------------------------------------------------------
# AWS S3 Client Initialization
# -------------------------------------------------------------
s3_client = None
if not app.config["USE_LOCAL_STORAGE"]:
    try:
        s3_client = boto3.client("s3", region_name=app.config["AWS_REGION"])
    except Exception as e:
        print(f"[WARN] Failed to initialize boto3 S3 client: {e}")

# -------------------------------------------------------------
# Database Helper Functions
# -------------------------------------------------------------
def ensure_database():
    """Connects to MySQL server and creates the target database if it doesn't exist yet."""
    if not app.config["USE_SQLITE"] and app.config["DB_HOST"]:
        try:
            conn = pymysql.connect(
                host=app.config["DB_HOST"],
                port=app.config["DB_PORT"],
                user=app.config["DB_USER"],
                password=app.config["DB_PASSWORD"],
                connect_timeout=5,
                autocommit=True
            )
            with conn.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{app.config['DB_NAME']}` DEFAULT CHARACTER SET utf8mb4;")
            conn.close()
            print(f"[INFO] Ensured database `{app.config['DB_NAME']}` exists.")
        except Exception as e:
            print(f"[WARN] ensure_database error: {e}")

def get_db_connection():
    """Returns a connection to AWS RDS MySQL or fallback SQLite."""
    if app.config["USE_SQLITE"]:
        conn = sqlite3.connect("diary.db")
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"
    else:
        try:
            conn = pymysql.connect(
                host=app.config["DB_HOST"],
                port=app.config["DB_PORT"],
                user=app.config["DB_USER"],
                password=app.config["DB_PASSWORD"],
                database=app.config["DB_NAME"],
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=5,
                autocommit=True
            )
            return conn, "mysql"
        except pymysql.err.OperationalError as e:
            # Error 1049: Unknown database -> create it automatically and reconnect
            if len(e.args) > 0 and e.args[0] == 1049:
                ensure_database()
                conn = pymysql.connect(
                    host=app.config["DB_HOST"],
                    port=app.config["DB_PORT"],
                    user=app.config["DB_USER"],
                    password=app.config["DB_PASSWORD"],
                    database=app.config["DB_NAME"],
                    cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=5,
                    autocommit=True
                )
                return conn, "mysql"
            raise

def init_db():
    """Initializes diary_entries table if it doesn't exist and migrates columns."""
    try:
        conn, db_type = get_db_connection()
        with conn:
            if db_type == "sqlite":
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS diary_entries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        content TEXT NOT NULL,
                        mood TEXT DEFAULT 'calm',
                        image_s3_key TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                # Migrate mood column if table already existed without it
                try:
                    cursor.execute("ALTER TABLE diary_entries ADD COLUMN mood TEXT DEFAULT 'calm'")
                except Exception:
                    pass
                conn.commit()
            else:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS diary_entries (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            title VARCHAR(255) NOT NULL,
                            content TEXT NOT NULL,
                            mood VARCHAR(50) DEFAULT 'calm',
                            image_s3_key VARCHAR(255),
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                    """)
                    try:
                        cursor.execute("ALTER TABLE diary_entries ADD COLUMN mood VARCHAR(50) DEFAULT 'calm'")
                    except Exception:
                        pass
        conn.close()
        print("[INFO] Database initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to initialize database: {e}")

# Call init_db on startup
with app.app_context():
    init_db()

# -------------------------------------------------------------
# Storage Helpers (S3 & Local)
# -------------------------------------------------------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

def upload_image(file_obj):
    """
    Uploads an image file to AWS S3 (or local storage fallback).
    Returns the storage key/filename.
    """
    if not file_obj or file_obj.filename == "":
        return None

    if not allowed_file(file_obj.filename):
        raise ValueError("Invalid file extension. Allowed: PNG, JPG, JPEG, GIF, WEBP.")

    orig_ext = file_obj.filename.rsplit(".", 1)[1].lower()
    unique_key = f"diary-{uuid.uuid4().hex[:12]}.{orig_ext}"

    if not app.config["USE_LOCAL_STORAGE"] and s3_client:
        # Upload directly to private AWS S3 bucket
        s3_client.upload_fileobj(
            file_obj,
            app.config["S3_BUCKET_NAME"],
            unique_key,
            ExtraArgs={"ContentType": file_obj.content_type or "image/jpeg"}
        )
        return unique_key
    else:
        # Fallback to local static/uploads/
        dest_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_key)
        file_obj.save(dest_path)
        return unique_key

def get_image_url(image_key):
    """
    Generates a secure temporary presigned URL for private S3 images,
    or returns a local static URL.
    """
    if not image_key:
        return None

    if not app.config["USE_LOCAL_STORAGE"] and s3_client:
        try:
            # Generate a 1-hour presigned URL from private S3 bucket
            url = s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": app.config["S3_BUCKET_NAME"], "Key": image_key},
                ExpiresIn=3600
            )
            return url
        except Exception as e:
            print(f"[ERROR] Presigned URL generation failed: {e}")
            return None
    else:
        return url_for("static", filename=f"uploads/{image_key}")

def delete_image(image_key):
    """Deletes image from AWS S3 or local storage."""
    if not image_key:
        return

    if not app.config["USE_LOCAL_STORAGE"] and s3_client:
        try:
            s3_client.delete_object(Bucket=app.config["S3_BUCKET_NAME"], Key=image_key)
        except Exception as e:
            print(f"[ERROR] Failed to delete S3 object {image_key}: {e}")
    else:
        dest_path = os.path.join(app.config["UPLOAD_FOLDER"], image_key)
        if os.path.exists(dest_path):
            os.remove(dest_path)

# -------------------------------------------------------------
# AWS Architecture Metadata & Diagnostics Helpers
# -------------------------------------------------------------
def get_ec2_metadata():
    """
    Attempts to read EC2 metadata via IMDSv2.
    Demonstrates that the app is running inside the VPC/EC2 layer.
    """
    try:
        # IMDSv2 token request (0.4s timeout so local dev doesn't hang)
        token_req = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
            method="PUT"
        )
        with urllib.request.urlopen(token_req, timeout=0.4) as resp:
            token = resp.read().decode("utf-8")

        def query_meta(path):
            req = urllib.request.Request(
                f"http://169.254.169.254/latest/meta-data/{path}",
                headers={"X-aws-ec2-metadata-token": token}
            )
            with urllib.request.urlopen(req, timeout=0.4) as r:
                return r.read().decode("utf-8")

        return {
            "is_ec2": True,
            "instance_id": query_meta("instance-id"),
            "availability_zone": query_meta("placement/availability-zone"),
            "local_ipv4": query_meta("local-ipv4"),
            "public_ipv4": query_meta("public-ipv4")
        }
    except Exception:
        return {
            "is_ec2": False,
            "instance_id": "Dev-LocalHost",
            "availability_zone": "Local / Non-EC2",
            "local_ipv4": "127.0.0.1",
            "public_ipv4": "N/A"
        }

def format_entry_date(date_val):
    """Formats datetime into a cozy journal date string like 'Sunday, Oct 11 • 7:45 PM'."""
    if not date_val:
        return ""
    try:
        if isinstance(date_val, str):
            dt = datetime.strptime(date_val, "%Y-%m-%d %H:%M:%S")
        else:
            dt = date_val
        return dt.strftime("%A, %b %d • %I:%M %p")
    except Exception:
        return str(date_val)

# -------------------------------------------------------------
# Application Routes
# -------------------------------------------------------------
@app.route("/")
def index():
    """Main Diary page listing all entries."""
    entries = []
    db_status = "Disconnected"
    
    try:
        conn, db_type = get_db_connection()
        if db_type == "sqlite":
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, content, image_s3_key, created_at FROM diary_entries ORDER BY id DESC")
            raw_entries = cursor.fetchall()
            entries = [
                {
                    "id": r["id"],
                    "title": r["title"],
                    "content": r["content"],
                    "image_url": get_image_url(r["image_s3_key"]),
                    "created_at": r["created_at"],
                    "display_date": format_entry_date(r["created_at"])
                }
                for r in raw_entries
            ]
        else:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id, title, content, image_s3_key, created_at FROM diary_entries ORDER BY id DESC")
                raw_entries = cursor.fetchall()
                entries = [
                    {
                        "id": r["id"],
                        "title": r["title"],
                        "content": r["content"],
                        "image_url": get_image_url(r["image_s3_key"]),
                        "created_at": r["created_at"],
                        "display_date": format_entry_date(r["created_at"])
                    }
                    for r in raw_entries
                ]
        conn.close()
        db_status = "Connected"
    except Exception as e:
        flash(f"Database error: {str(e)}", "danger")

    ec2_info = get_ec2_metadata()
    today_str = datetime.now().strftime("%A, %B %d, %Y")
    return render_template(
        "index.html",
        entries=entries,
        ec2_info=ec2_info,
        db_status=db_status,
        today_str=today_str,
        config=app.config
    )

@app.route("/entries", methods=["POST"])
def create_entry():
    """Handles submission of a new diary entry and optional image upload."""
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    image_file = request.files.get("image")

    if not title or not content:
        flash("Title and Content are required.", "warning")
        return redirect(url_for("index"))

    image_key = None
    if image_file and image_file.filename:
        try:
            image_key = upload_image(image_file)
        except Exception as e:
            flash(f"Image upload failed: {str(e)}", "danger")
            return redirect(url_for("index"))

    try:
        conn, db_type = get_db_connection()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if db_type == "sqlite":
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO diary_entries (title, content, image_s3_key, created_at) VALUES (?, ?, ?, ?)",
                (title, content, image_key, now_str)
            )
            conn.commit()
        else:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO diary_entries (title, content, image_s3_key, created_at) VALUES (%s, %s, %s, %s)",
                    (title, content, image_key, now_str)
                )
        conn.close()
        flash("Entry saved to your journal.", "success")
    except Exception as e:
        flash(f"Failed to save entry: {str(e)}", "danger")

    return redirect(url_for("index"))

@app.route("/entries/<int:entry_id>/delete", methods=["POST"])
def delete_entry(entry_id):
    """Deletes an entry and cleans up its S3 image."""
    try:
        conn, db_type = get_db_connection()
        image_key = None
        if db_type == "sqlite":
            cursor = conn.cursor()
            cursor.execute("SELECT image_s3_key FROM diary_entries WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            if row:
                image_key = row["image_s3_key"]
            cursor.execute("DELETE FROM diary_entries WHERE id = ?", (entry_id,))
            conn.commit()
        else:
            with conn.cursor() as cursor:
                cursor.execute("SELECT image_s3_key FROM diary_entries WHERE id = %s", (entry_id,))
                row = cursor.fetchone()
                if row:
                    image_key = row["image_s3_key"]
                cursor.execute("DELETE FROM diary_entries WHERE id = %s", (entry_id,))
        conn.close()

        if image_key:
            delete_image(image_key)

        flash("Diary entry deleted successfully.", "info")
    except Exception as e:
        flash(f"Failed to delete entry: {str(e)}", "danger")

    return redirect(url_for("index"))

@app.route("/api/status")
def architecture_status():
    """
    Live diagnostics endpoint returning connectivity status for:
    - EC2 Compute Layer (Instance ID, AZ, Private IP)
    - RDS Database Layer in Private Subnet (Ping, Latency, Engine)
    - S3 Storage Layer (IAM access, Bucket reachability, Object count)
    """
    ec2_info = get_ec2_metadata()
    
    # 1. Test RDS Database Connectivity
    rds_status = {"connected": False, "latency_ms": 0, "engine": "Unknown", "error": None}
    t0 = time.time()
    try:
        conn, db_type = get_db_connection()
        if db_type == "sqlite":
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            rds_status["engine"] = "SQLite (Local Fallback)"
        else:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            rds_status["engine"] = f"MySQL RDS ({app.config['DB_HOST']})"
        conn.close()
        rds_status["connected"] = True
        rds_status["latency_ms"] = round((time.time() - t0) * 1000, 2)
    except Exception as e:
        rds_status["error"] = str(e)

    # 2. Test S3 Storage Connectivity
    s3_status = {"connected": False, "bucket": app.config["S3_BUCKET_NAME"], "auth": "None", "error": None}
    if not app.config["USE_LOCAL_STORAGE"] and s3_client:
        try:
            s3_client.head_bucket(Bucket=app.config["S3_BUCKET_NAME"])
            s3_status["connected"] = True
            s3_status["auth"] = "EC2 IAM Instance Profile / Boto3"
        except Exception as e:
            s3_status["error"] = str(e)
    else:
        s3_status["connected"] = True
        s3_status["auth"] = "Local Filesystem Fallback (static/uploads)"

    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "ec2": ec2_info,
        "rds": rds_status,
        "s3": s3_status
    })

@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)
