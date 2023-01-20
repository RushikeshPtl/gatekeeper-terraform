resource "aws_iam_role" "role" {
  name = "${var.env}-${var.project_name}-${var.name}-role"

  assume_role_policy = file(var.role_file_path)
}

resource "aws_iam_policy" "policy" {
  name   = "${var.env}-${var.project_name}-${var.name}-role-policy"
  policy = file(var.policy_file_path)
}

resource "aws_iam_role_policy_attachment" "role_policy" {
  role       = aws_iam_role.role.name
  policy_arn = aws_iam_policy.policy.arn
}
