resource "aws_iam_role" "role" {
  name = replace("${var.env}-${var.project_name}-${var.name}-role", "_", "-")

  assume_role_policy = file(var.role_file_path)
}

resource "aws_iam_policy" "policy" {
  name   = replace("${var.env}-${var.project_name}-${var.name}-role-policy", "_", "-")
  policy = file(var.policy_file_path)
}

resource "aws_iam_role_policy_attachment" "role_policy" {
  role       = aws_iam_role.role.name
  policy_arn = aws_iam_policy.policy.arn
}
