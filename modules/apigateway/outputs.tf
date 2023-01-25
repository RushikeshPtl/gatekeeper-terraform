output "base_url" {
  description = "Base URL for API Gateway stage."
  value       = aws_apigatewayv2_stage.apigateway_stage.invoke_url
}

output "api_id" {
  description = "Base URL for API Gateway stage."
  value       = aws_apigatewayv2_api.apigateway.id
}


output "execution_arn" {
  description = "Base URL for API Gateway stage."
  value =  aws_apigatewayv2_api.apigateway.execution_arn
}
