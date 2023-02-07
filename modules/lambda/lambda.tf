# Define a local variable for the Lambda function
# source code path in order to avoid repetitions.
locals {
  # Relative paths change if this configuration is
  # included as a module from Terragrunt.
  lambda_source_path = "${path.module}${var.lambda_relative_path}src/${var.module_name}/${var.function_name}/app.py"
  lambda_output_path = "${path.module}${var.lambda_relative_path}src/${var.module_name}/${var.function_name}/${var.function_name}.zip"
}

# Create an archive form the Lambda source code,
# filtering out unneeded files.

data "archive_file" "lambda_source_package" {
  type        = "zip"
  source_file = local.lambda_source_path
  output_path = local.lambda_output_path
}

resource "aws_lambda_function" "lambda_function" {
  function_name    = replace("${var.env}-${var.project_name}-${var.function_name}", "_", "-")
  runtime          = var.runtime
  handler          = var.handler
  filename         = data.archive_file.lambda_source_package.output_path
  source_code_hash = filebase64sha256(data.archive_file.lambda_source_package.output_path)
  role             = aws_iam_role.function_role.arn
  layers           = var.layers
  timeout          = var.timeout
  memory_size      = var.memory_size

  environment {
    variables = var.environment_variables
  }
  vpc_config {
       subnet_ids         = var.include_vpc ? var.subnet_ids : []
       security_group_ids = var.include_vpc ? var.security_group_ids : []
  }
}

resource "aws_cloudwatch_event_rule" "schedule" {
  count               = var.warmup_enabled ? 1 : 0
  name                = replace("${var.function_name}WarmUpSchedule", "_", "")
  description         = "Schedule for Lambda Function"
  schedule_expression = var.schedule
}

resource "aws_cloudwatch_event_target" "schedule_lambda" {
  count     = var.warmup_enabled ? 1 : 0
  rule      = aws_cloudwatch_event_rule.schedule[count.index].name
  target_id = "processing_lambda"
  arn       = aws_lambda_function.lambda_function.arn
}


resource "aws_lambda_permission" "allow_events_bridge_to_run_lambda" {
  count         = var.warmup_enabled ? 1 : 0
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_function.function_name
  principal     = "events.amazonaws.com"
}

data "aws_iam_policy_document" "lambda_trust_policy" {
  statement {
    actions       = ["sts:AssumeRole"]
    effect        = "Allow"
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "function_role" {
  name               = replace("${var.env}-${var.project_name}-${var.function_name}-role", "_", "-")
  assume_role_policy = data.aws_iam_policy_document.lambda_trust_policy.json
}

resource "aws_iam_role_policy_attachment" "lambda_basic_execution_role" {
  role       = aws_iam_role.function_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "policies" {
  count      = length(var.policies)
  role       = aws_iam_role.function_role.name
  policy_arn = var.policies[count.index]
}

resource "aws_apigatewayv2_integration" "apigateway_integration" {
  count              = length(var.api_paths)
  api_id             = var.apigateway_id
  integration_uri    = aws_lambda_function.lambda_function.arn
  integration_type   = "AWS_PROXY"
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "apigateway_route" {
  count     = length(var.api_paths)
  api_id    = var.apigateway_id
  route_key = "${var.api_paths[count.index].method} ${var.api_paths[count.index].path}"
  target    = "integrations/${aws_apigatewayv2_integration.apigateway_integration[count.index].id}"
}

resource "aws_lambda_permission" "lambda_permission" {
  count         = length(var.api_paths)
  statement_id  = length(var.api_paths) == 1 ? "AllowExecutionFromAPIGateway" : "AllowExecutionFromAPIGateway-${count.index}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${var.apigateway_execution_arn}/*/*"
}

resource "aws_lambda_event_source_mapping" "example" {
  count             = length(var.event_source_arns)
  event_source_arn  = var.event_source_arns[count.index]
  function_name     = aws_lambda_function.lambda_function.arn
  batch_size        = 1
  starting_position = "LATEST"
}
