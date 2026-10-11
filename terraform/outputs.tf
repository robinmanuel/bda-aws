output "application_url" {
  description = "Public URL to access the Personal Diary Web App"
  value       = "http://${aws_instance.app_server.public_ip}"
}

output "ec2_public_ip" {
  description = "Public IPv4 of the EC2 Instance"
  value       = aws_instance.app_server.public_ip
}

output "ec2_private_ip" {
  description = "Private IP of the EC2 Instance in the Public Subnet"
  value       = aws_instance.app_server.private_ip
}

output "rds_private_endpoint" {
  description = "Private RDS MySQL Endpoint (unreachable from the Internet)"
  value       = aws_db_instance.mysql.address
}

output "s3_bucket_name" {
  description = "Name of the S3 Bucket storing diary images"
  value       = aws_s3_bucket.diary_storage.bucket
}

output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}
