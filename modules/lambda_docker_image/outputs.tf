output "invoke_arn" {
  description = "Invoke ARN of Lambda Function"
  value       = aws_lambda_function.lambda_function.invoke_arn

}

output "resource_arn" {
  description = "Resource ARN of Lambda Function"
  value       = aws_lambda_function.lambda_function.arn
}

output "function_name" {
  description = "Name of the Lambda Function."
  value       = aws_lambda_function.lambda_function.function_name
}

