
resource "aws_apigatewayv2_api" "apigateway" {
  name          = replace("${var.env}-${var.project_name}-${var.name}-gw", "_", "-")
  protocol_type = "HTTP"
  cors_configuration = {
    allow_headers = ["Authorization", "Content-Type""X-Amz-Date", "X-Amz-Security-Token", "X-Api-Key"]
    allow_methods = ["OPTIONS", "HEAD", "GET", "POST", "PUT", "PATCH", "DELETE"]
    allow_origin  = "*"
  }
}

resource "aws_apigatewayv2_stage" "apigateway_stage" {
  api_id      = aws_apigatewayv2_api.apigateway.id
  name        = var.stage
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gw.arn
    format = jsonencode({
      requestId               = "$context.requestId"
      sourceIp                = "$context.identity.sourceIp"
      requestTime             = "$context.requestTime"
      protocol                = "$context.protocol"
      httpMethod              = "$context.httpMethod"
      resourcePath            = "$context.resourcePath"
      routeKey                = "$context.routeKey"
      status                  = "$context.status"
      responseLength          = "$context.responseLength"
      integrationErrorMessage = "$context.integrationErrorMessage"
      }
    )
  }
}

resource "aws_cloudwatch_log_group" "api_gw" {
  name              = replace("/aws/api_gw/${aws_apigatewayv2_api.apigateway.name}", "_", "-")
  retention_in_days = 30
}

