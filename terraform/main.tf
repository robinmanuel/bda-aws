terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.5"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_availability_zones" "available" {
  state = "available"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# ==============================================================================
# 1. NETWORKING (VPC, Public & Private Subnets)
# ==============================================================================
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-vpc"
  }
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-igw"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-public-subnet"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }

  tags = {
    Name = "${var.project_name}-public-rt"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# Private Subnets for RDS (spanning 2 AZs)
resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = {
    Name = "${var.project_name}-private-subnet-1"
  }
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.3.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = {
    Name = "${var.project_name}-private-subnet-2"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-private-rt"
  }
}

resource "aws_route_table_association" "private_1" {
  subnet_id      = aws_subnet.private_1.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_2" {
  subnet_id      = aws_subnet.private_2.id
  route_table_id = aws_route_table.private.id
}

# ==============================================================================
# 2. SECURITY GROUPS (App & Database Isolation)
# ==============================================================================
resource "aws_security_group" "ec2_sg" {
  name        = "${var.project_name}-ec2-sg"
  description = "Security Group for EC2 Web Server"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Public HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH Admin"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ec2-sg"
  }
}

resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg"
  description = "Security Group for RDS MySQL - Inbound only from EC2"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MySQL from EC2 Security Group Only"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

# ==============================================================================
# 3. STORAGE LAYER (AWS S3) & IAM INSTANCE PROFILE
# ==============================================================================
resource "aws_s3_bucket" "diary_storage" {
  bucket        = "${var.project_name}-storage-${random_id.bucket_suffix.hex}"
  force_destroy = true

  tags = {
    Name = "${var.project_name}-bucket"
  }
}

resource "aws_s3_bucket_public_access_block" "diary_storage_block" {
  bucket = aws_s3_bucket.diary_storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_iam_role" "ec2_s3_role" {
  name = "${var.project_name}-ec2-s3-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_policy" "s3_access_policy" {
  name        = "${var.project_name}-s3-access-policy"
  description = "Allows EC2 instance to upload and download diary photos in S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.diary_storage.arn,
          "${aws_s3_bucket.diary_storage.arn}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "attach_s3" {
  role       = aws_iam_role.ec2_s3_role.name
  policy_arn = aws_iam_policy.s3_access_policy.arn
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_s3_role.name
}

# ==============================================================================
# 4. DATABASE LAYER (AWS RDS MySQL in Private Subnet)
# ==============================================================================
resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "${var.project_name}-subnet-group"
  subnet_ids = [aws_subnet.private_1.id, aws_subnet.private_2.id]

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

resource "aws_db_instance" "mysql" {
  identifier             = "${var.project_name}-db"
  engine                 = "mysql"
  engine_version         = "8.0"
  instance_class         = "db.t3.micro"
  allocated_storage      = 20
  db_name                = "diarydb"
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  publicly_accessible    = false
  skip_final_snapshot    = true

  tags = {
    Name = "${var.project_name}-rds-db"
  }
}

# ==============================================================================
# 5. COMPUTE LAYER (AWS EC2 in Public Subnet)
# ==============================================================================
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

resource "aws_instance" "app_server" {
  ami                  = data.aws_ami.amazon_linux_2023.id
  instance_type        = var.instance_type
  subnet_id            = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ec2_sg.id]
  iam_instance_profile = aws_iam_instance_profile.ec2_profile.name

  depends_on = [aws_db_instance.mysql]

  user_data = <<-EOF
              #!/bin/bash
              set -ex
              dnf update -y
              dnf install -y python3.11 python3.11-pip git

              APP_DIR="/opt/diary-app"
              mkdir -p "$APP_DIR"
              cd "$APP_DIR"

              git clone https://github.com/robinmanuel/bda-aws.git repo_temp || true
              if [ -d "repo_temp/app" ]; then
                  cp -r repo_temp/app/* "$APP_DIR/"
                  rm -rf repo_temp
              fi

              python3.11 -m venv venv
              source venv/bin/activate
              pip install --upgrade pip
              pip install flask pymysql cryptography boto3 python-dotenv gunicorn werkzeug

              cat <<EOT > "$APP_DIR/.env"
              DB_HOST=${aws_db_instance.mysql.address}
              DB_PORT=3306
              DB_USER=${var.db_username}
              DB_PASSWORD=${var.db_password}
              DB_NAME=diarydb
              S3_BUCKET_NAME=${aws_s3_bucket.diary_storage.bucket}
              AWS_REGION=${var.aws_region}
              PORT=80
              EOT

              mkdir -p "$APP_DIR/static/uploads"
              chmod -R 755 "$APP_DIR"

              cat <<EOT > /etc/systemd/system/diary.service
              [Unit]
              Description=AWS Personal Diary Application
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
              EOT

              systemctl daemon-reload
              systemctl enable diary.service
              systemctl restart diary.service
              EOF

  tags = {
    Name = "${var.project_name}-ec2"
  }
}
