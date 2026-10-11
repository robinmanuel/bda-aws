# AWS 3-Tier Personal Diary Architecture

This project implements a secure, decoupled 3-tier cloud architecture designed to demonstrate defense-in-depth on AWS using **VPC, Public/Private Subnets, EC2, RDS, and S3**.

---

## 1. Architecture Topology Diagram

```mermaid
flowchart TB
    subgraph Internet ["🌐 Public Internet"]
        User["User Browser / Client"]
    end

    subgraph AWSCloud ["☁️ AWS Cloud Region"]
        subgraph VPC ["Custom VPC (10.0.0.0/16)"]
            IGW["Internet Gateway (IGW)"]

            subgraph PublicSubnet ["Public Subnet (10.0.1.0/24)"]
                EC2["EC2 Instance (Amazon Linux 2023)<br/>Flask + Gunicorn<br/>Port 80 (HTTP)"]
                EC2SG["Security Group: EC2-SG<br/>Inbound: 80, 22 (0.0.0.0/0)"]
            end

            subgraph PrivateSubnets ["Private Subnets (No IGW Route)"]
                subgraph PrivateSubnet1 ["Private Subnet 1 (10.0.2.0/24)"]
                    RDS["AWS RDS MySQL 8.0<br/>Port 3306"]
                end
                subgraph PrivateSubnet2 ["Private Subnet 2 (10.0.3.0/24)"]
                    RDSStandby["Standby Subnet Group"]
                end
                RDSSG["Security Group: RDS-SG<br/>Inbound: 3306 (Source: EC2-SG only)"]
            end
        end

        subgraph S3Service ["AWS S3 Storage Layer"]
            S3["Private S3 Bucket<br/>(Block Public Access: ON)<br/>Diary Image Attachments"]
        end

        IAM["IAM Role & Instance Profile<br/>(s3:PutObject, s3:GetObject)"]
    end

    User -->|HTTP Port 80| IGW
    IGW -->|Route Table 0.0.0.0/0| EC2
    EC2 --- EC2SG

    EC2 -->|SQL Queries (Port 3306)| RDS
    RDS --- RDSSG

    EC2 -.->|Assumes Role via IMDSv2| IAM
    IAM -.->|Grants Access| S3
    EC2 -->|boto3 API (Upload / Presigned URLs)| S3
```

---

## 2. Layer-by-Layer Security Breakdown

| Layer | AWS Component | Placement | Security Controls |
| :--- | :--- | :--- | :--- |
| **Networking** | AWS VPC | `10.0.0.0/16` | Fully isolated software-defined network boundary with DNS resolution. |
| **Edge / Gateway** | Internet Gateway | VPC Root | Only routes traffic to/from the Public Subnet route table. |
| **Compute / Web** | EC2 (`t3.micro`) | Public Subnet (`10.0.1.0/24`) | Security Group allows inbound port 80 (HTTP) and port 22 (SSH). No database ports exposed. |
| **Database** | RDS MySQL (`db.t3.micro`) | Private Subnets (`10.0.2.0/24`, `10.0.3.0/24`) | **Strict Network Isolation:** <br>1. Subnet route table has **no route** to Internet Gateway.<br>2. `PubliclyAccessible = false` (no public IP).<br>3. Security Group allows port 3306 **only** when source is `EC2-SG`. |
| **Object Storage** | AWS S3 Bucket | AWS S3 Service | **Zero Hardcoded Secrets:**<br>1. Block Public Access enabled (100% private).<br>2. EC2 authenticates via IAM Role (`DiaryApp-EC2-Role`).<br>3. Web clients view images via secure, expiring Presigned URLs. |

---

## 3. How Secure Communication is Demonstrated

1. **Application ➔ Database (EC2 to RDS)**:
   - The RDS endpoint (e.g., `personaldiary-db.xxxx.us-east-1.rds.amazonaws.com`) resolves to a private IP within `10.0.2.0/24`.
   - Any external client attempting to connect to this endpoint directly from their home PC will fail/timeout immediately.
   - Only the EC2 instance inside the VPC whose Security Group matches `EC2-SG` can open a TCP handshake on port 3306.

2. **Application ➔ Cloud Storage (EC2 to S3)**:
   - No AWS Access Key ID or Secret Access Key is written in `.env`, config files, or git.
   - The Boto3 SDK running on EC2 automatically fetches short-lived credentials from AWS Instance Metadata Service (IMDSv2).
   - When a user uploads a photo, the Flask backend uploads it to S3, and generates a signed URL with 1-hour validity so only authorized viewers can see the image.
