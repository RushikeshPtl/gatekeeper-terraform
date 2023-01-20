resource "aws_iam_role" "role" {
  name = "${var.name}-sfn-state-machine-role"

  assume_role_policy = file(var.role_file_path)
}

resource "aws_iam_policy" "policy" {
  name   = "${var.name}-sfn-state-machine-policy"
  policy = file(var.policy_file_path)
}

resource "aws_iam_role_policy_attachment" "role_policy" {
  role       = aws_iam_role.role.name
  policy_arn = aws_iam_policy.policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_policy" {
  role       = aws_iam_role.role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

data "aws_iam_policy_document" "invoke_functions" {
  statement {
    effect = "Allow"
    actions = [
      "lambda:InvokeFunction"
    ]
    resources = var.function_arns
  }
}

resource "aws_iam_policy" "invoke_functions" {
  name   = "${var.name}-sfn-state-machine-invoke-functions"
  policy = data.aws_iam_policy_document.invoke_functions.json
}

resource "aws_iam_role_policy_attachment" "invoke_functions_policy" {
  role       = aws_iam_role.role.name
  policy_arn = aws_iam_policy.invoke_functions.arn
}

resource "aws_sfn_state_machine" "sfn_state_machine" {
  name       = "${var.env}-${var.project_name}-${var.name}"
  role_arn   = aws_iam_role.role.arn
  type       = var.type
  definition = templatefile(var.template_file_path, var.template_vars)
}
