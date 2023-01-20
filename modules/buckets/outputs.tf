output "lambda_bucket_id" {
  description = "The name of the bucket that is stores function"
  value       = aws_s3_bucket.lambda.id
}

