variable "aws_region" {
  description = "AWS Region to deploy resources"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name prefix for AWS resources"
  type        = string
  default     = "personal-diary"
}

variable "db_username" {
  description = "Master username for RDS MySQL database"
  type        = string
  default     = "admin"
}

variable "db_password" {
  description = "Master password for RDS MySQL database"
  type        = string
  sensitive   = true
  default     = "DiaryPass2026!"
}

variable "instance_type" {
  description = "EC2 instance size"
  type        = string
  default     = "t3.micro"
}
