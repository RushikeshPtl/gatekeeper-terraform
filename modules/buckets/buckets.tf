resource "random_pet" "lambda" {
  prefix = "${var.env}-${var.project_name}-${var.prefix}"
  length = 4
}

resource "aws_s3_bucket" "lambda" {
  bucket        = random_pet.lambda.id
  force_destroy = true
}

resource "aws_s3_bucket_acl" "lambda" {
  bucket = aws_s3_bucket.lambda.id
  acl    = "private"
}

resource "aws_s3_bucket_versioning" "versioning" {
  bucket = aws_s3_bucket.lambda.id
  versioning_configuration {
    status = "Enabled"
  }
}
