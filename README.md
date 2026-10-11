# CloudDiary: 3-Tier AWS Personal Diary Application

A clean, modern, and lightweight cloud application designed to demonstrate secure communication across AWS **VPC**, **Public & Private Subnets**, **EC2**, **RDS**, and **S3**.

![AWS 3-Tier Architecture](https://img.shields.io/badge/AWS-VPC%20%7C%20EC2%20%7C%20RDS%20%7C%20S3-FF9900?logo=amazon-aws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-Web%20Framework-000000?logo=flask&logoColor=white)
![MySQL](https://img.shields.io/badge/Database-AWS%20RDS%20MySQL-4479A1?logo=mysql&logoColor=white)

---

## 🎯 Architecture & Objectives

The goal of this application is to reliably and simply demonstrate secure multi-tier communication in the cloud:

```
[ Public Internet / User Browser ]
               │
               ▼ HTTP (Port 80)
   ┌───────────────────────────────────────────────┐
   │ AWS VPC (10.0.0.0/16)                         │
   │                                               │
   │  ┌─────────────────────────────────────────┐  │
   │  │ Public Subnet (10.0.1.0/24)             │  │
   │  │   ⚡ EC2 Web Server (Flask + Gunicorn)  │  │
   │  └───────────────┬─────────────────────────┘  │
   │                  │                            │
   │                  │ Port 3306 (MySQL)          │
   │                  │ (Allowed ONLY from EC2-SG) │
   │                  ▼                            │
   │  ┌─────────────────────────────────────────┐  │
   │  │ Private Subnets (10.0.2.0/24, .3.0/24)  │  │
   │  │   🗄️ AWS RDS MySQL (db.t3.micro)        │  │
   │  │   * Isolated: No Public IP, No IGW Route│  │
   │  └─────────────────────────────────────────┘  │
   └──────────────────┬────────────────────────────┘
                      │
                      │ IAM Role (Zero Hardcoded Keys)
                      ▼
   ┌───────────────────────────────────────────────┐
   │ 🪣 AWS S3 Bucket (Private Photo Storage)      │
   │    * Block Public Access: ON                  │
   │    * Secure Temporary Presigned URLs          │
   └───────────────────────────────────────────────┘
```

### Key Demonstrations:
1. **VPC & Subnet Isolation**:
   - **Public Subnet**: Houses the EC2 Web Server with an Internet Gateway (IGW) route to receive user HTTP requests.
   - **Private Subnets**: Houses the RDS MySQL database across 2 Availability Zones with **no route to the Internet Gateway** and **no public IP address**.
2. **Secure App-to-Database Layer (EC2 ➔ RDS)**:
   - The RDS Security Group allows inbound port `3306` **strictly from the EC2 Security Group** (`Source: EC2-SG`). Direct internet connections to RDS are physically blocked by AWS.
3. **Secure App-to-Storage Layer (EC2 ➔ S3)**:
   - The EC2 instance accesses S3 using an attached **AWS IAM Instance Profile**.
   - **Zero API keys or passwords** are hardcoded in code or pushed to Git.
   - S3 bucket has **Block Public Access** enabled. Diary images are served to the user using short-lived (1-hour) **Presigned URLs**.
4. **Live Architecture Diagnostics Dashboard**:
   - The web UI features a live **Architecture & Topology Status Bar** that pings RDS, inspects S3, and queries the EC2 Instance Metadata Service (IMDSv2) in real time to prove all 3 tiers are active and secure.

---

## 📁 Repository Structure

```
bda-aws/
├── app/
│   ├── app.py                 # Flask web application & AWS API handlers
│   ├── config.py              # Environment configuration (RDS, S3, fallback)
│   ├── requirements.txt       # Dependencies (Flask, PyMySQL, Boto3, Gunicorn)
│   ├── static/
│   │   ├── style.css          # Modern dark-mode UI & topology styles
│   │   └── app.js             # Live AWS status poller & image preview
│   └── templates/
│       └── index.html         # Personal Diary UI with live AWS architecture status
├── cloudformation/
│   └── template.yaml          # 1-Click AWS CloudFormation deployment template
├── terraform/
│   ├── main.tf                # Complete VPC, Subnet, EC2, RDS, S3 Terraform script
│   ├── variables.tf           # Configurable deployment parameters
│   └── outputs.tf             # App URL, RDS endpoint, S3 bucket outputs
├── scripts/
│   └── user_data.sh           # EC2 User Data script to auto-bootstrap application
├── architecture/
│   └── ARCHITECTURE.md        # Detailed security flow & Mermaid topology diagram
└── README.md                  # Project documentation & deployment guide
```

---

## 🚀 Deployment Options

You can deploy this project using either **AWS CloudFormation (Easiest)**, **Terraform**, or **Step-by-Step Manual Console**.

---

### Option 1: 1-Click AWS CloudFormation (Recommended)

Requires zero local installations (no Terraform or AWS CLI needed).

1. Log into your [AWS Management Console](https://console.aws.amazon.com/).
2. Navigate to **CloudFormation** (ensure you are in your desired region, e.g., `us-east-1`).
3. Click **Create stack** ➔ **With new resources (standard)**.
4. Select **Upload a template file** and choose [`cloudformation/template.yaml`](file:///c:/Users/Robin%20Manuel/OneDrive/Documents/GitHub/bda-aws/cloudformation/template.yaml).
5. Click **Next** and configure:
   - **Stack name**: `PersonalDiaryApp`
   - **DBPassword**: Enter a secure password for MySQL (e.g., `DiarySecurePass2026!`).
6. Click **Next** ➔ **Next**, check the box:
   - ☑️ *I acknowledge that AWS CloudFormation might create IAM resources.*
7. Click **Submit**.
8. Wait ~6 to 8 minutes for AWS to provision the VPC, Subnets, RDS MySQL, S3 Bucket, and EC2 instance.
9. Go to the **Outputs** tab of your stack to find your **`ApplicationURL`**:
   ```
   ApplicationURL: http://<EC2-PUBLIC-IP>
   ```
10. Open the link in your browser!

---

### Option 2: Terraform (Infrastructure as Code)

If you have Terraform and AWS CLI configured locally:

1. Navigate to the terraform directory:
   ```bash
   cd terraform
   ```
2. Initialize and deploy:
   ```bash
   terraform init
   terraform apply -auto-approve
   ```
3. Terraform will print the public application URL upon completion:
   ```bash
   Apply complete!
   Outputs:
   application_url = "http://54.xxx.xxx.xxx"
   rds_private_endpoint = "personal-diary-db.xxxx.us-east-1.rds.amazonaws.com"
   s3_bucket_name = "personal-diary-storage-a1b2c3d4"
   ```

---

### Option 3: Manual AWS Console Walkthrough

If completing this as a manual lab exercise:

<details>
<summary><b>Click to expand step-by-step AWS Console instructions</b></summary>

#### Step 1: Create Custom VPC & Subnets
1. Open **VPC Console** ➔ **Create VPC** ➔ Select **VPC and more**.
2. Name tag: `Diary-VPC`, IPv4 CIDR: `10.0.0.0/16`.
3. Number of Availability Zones: `2`.
4. Number of Public Subnets: `1` (`10.0.1.0/24`).
5. Number of Private Subnets: `2` (`10.0.2.0/24` and `10.0.3.0/24`).
6. NAT Gateways: **None** (to keep it free and simple).
7. VPC Endpoints: **None**.
8. Click **Create VPC**.

#### Step 2: Create Security Groups
1. Navigate to **Security Groups** ➔ **Create security group**:
   - **EC2-SG**:
     - VPC: `Diary-VPC`
     - Inbound rules:
       - HTTP (Port 80) from `0.0.0.0/0`
       - SSH (Port 22) from `0.0.0.0/0` (or your IP)
   - **RDS-SG**:
     - VPC: `Diary-VPC`
     - Inbound rules:
       - MySQL/Aurora (Port 3306) ➔ Source: Select `EC2-SG` (Security Group reference).
       - *Do not allow 0.0.0.0/0.*

#### Step 3: Create S3 Bucket & IAM Role
1. Navigate to **S3** ➔ **Create bucket**:
   - Bucket name: `diary-photos-<your-name>-<random-id>`
   - Region: Same region as VPC.
   - Keep **Block all public access** checked (Private bucket).
   - Click **Create bucket**.
2. Navigate to **IAM** ➔ **Roles** ➔ **Create role**:
   - Trusted entity type: **AWS Service** ➔ **EC2**.
   - Permissions: Attach policy with S3 read/write permissions (or attach `AmazonS3FullAccess` for lab simplicity).
   - Role name: `DiaryEC2S3Role`.
   - Click **Create role**.

#### Step 4: Create RDS MySQL in Private Subnet
1. Navigate to **RDS** ➔ **Subnet groups** ➔ **Create DB subnet group**:
   - Name: `diary-db-subnet-group`
   - VPC: `Diary-VPC`
   - Select the 2 Private Subnets created in Step 1.
2. Navigate to **Databases** ➔ **Create database**:
   - Engine: **MySQL** (version 8.0)
   - Template: **Free tier**
   - DB instance identifier: `diary-db`
   - Master username: `admin`
   - Master password: `DiaryPass2026!`
   - Instance class: `db.t3.micro`
   - Storage: 20 GB gp2
   - Connectivity:
     - VPC: `Diary-VPC`
     - DB Subnet Group: `diary-db-subnet-group`
     - Public access: **No**
     - Existing VPC security groups: Select `RDS-SG` (remove default).
   - Additional configuration: Initial database name: `diarydb`.
   - Click **Create database**.

#### Step 5: Launch EC2 Instance in Public Subnet
1. Navigate to **EC2** ➔ **Launch instances**:
   - Name: `Diary-App-Server`
   - AMI: **Amazon Linux 2023**
   - Instance type: `t3.micro` or `t2.micro`
   - Network settings:
     - VPC: `Diary-VPC`
     - Subnet: `Public Subnet`
     - Auto-assign public IP: **Enable**
     - Firewall: Select existing `EC2-SG`
   - Advanced details:
     - IAM instance profile: Select `DiaryEC2S3Role`
     - User data: Paste the contents of [`scripts/user_data.sh`](file:///c:/Users/Robin%20Manuel/OneDrive/Documents/GitHub/bda-aws/scripts/user_data.sh) replacing the environment variables with your RDS endpoint and S3 bucket name.
2. Click **Launch instance**.
3. Access your instance's public IP once ready.

</details>

---

## 🧪 Testing & Demonstration Guide

### 1. Web Application Features
- **Write an Entry**: Enter a title and reflection note.
- **Upload Photo**: Attach an image (e.g., JPEG, PNG). The server uploads the image to the private S3 bucket and records the reference in RDS.
- **View Timeline**: The entry displays with a secure temporary presigned image URL.
- **Delete Entry**: Deletes the database record and removes the image object from S3.

### 2. Validating Security Architecture for Evaluation

| Verification Check | How to Test | Expected Result |
| :--- | :--- | :--- |
| **EC2 Public Access** | Open `http://<EC2-PUBLIC-IP>` in your browser | Loads the Personal Diary dashboard successfully. |
| **RDS Network Isolation** | From your **local machine terminal** run:<br>`telnet <RDS-ENDPOINT> 3306` | **Connection times out / fails**. Proves database is invisible to the public internet. |
| **RDS Security Group Rule** | From inside the **EC2 instance** via SSH run:<br>`telnet <RDS-ENDPOINT> 3306` | **Connected**. Proves EC2 is allowed via Security Group rule. |
| **S3 Private Bucket Security** | Try accessing an image via its direct S3 URL:<br>`https://<bucket>.s3.amazonaws.com/<image-key>` | Returns **`403 Forbidden` (AccessDenied)**. Public access is blocked. |
| **S3 Presigned URL Delivery** | Click on the image thumbnail inside the Diary app | Opens with signed query parameters (`?AWSAccessKeyId=...&Signature=...`). |
| **Live Topology Dashboard** | Click **Refresh AWS Status** in the top navigation | Real-time pills show **EC2 ONLINE**, **CONNECTED** (with latency), and **S3 ONLINE**. |

---

## 💻 Local Offline Development (Fallback Mode)

You can test the application on your computer without connecting to AWS:

1. Clone the repository and navigate into it:
   ```bash
   cd bda-aws
   ```
2. Install dependencies:
   ```bash
   pip install -r app/requirements.txt
   ```
3. Run the Flask development server:
   ```bash
   python app/app.py
   ```
4. Open `http://127.0.0.1:5000` in your browser.
   - The app automatically detects that AWS RDS/S3 are not present and falls back gracefully to a local SQLite database (`diary.db`) and local uploads directory (`app/static/uploads/`).

---

## 🧹 Teardown & Resource Cleanup

To avoid ongoing charges on your AWS account after demonstration:

- **If deployed via CloudFormation**:
  1. Open AWS CloudFormation Console.
  2. Empty the S3 bucket if objects were uploaded (or delete objects in S3 console).
  3. Select `PersonalDiaryApp` stack and click **Delete**.
- **If deployed via Terraform**:
  ```bash
  cd terraform
  terraform destroy -auto-approve
  ```
- **If deployed Manually**:
  1. Terminate the EC2 instance.
  2. Delete the RDS MySQL database (choose "No final snapshot").
  3. Empty and delete the S3 bucket.
  4. Delete the VPC and Security Groups.

---

## 📜 License
MIT License. Built for cloud computing architecture demonstrations.
