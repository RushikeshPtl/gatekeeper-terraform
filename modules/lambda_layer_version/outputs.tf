output "layer_arn" {
  description = "ARN of the Lambda Layer with version."
  value       = aws_lambda_layer_version.lambda_layer.arn
}

