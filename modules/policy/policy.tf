resource "aws_iam_policy" "policy" {
  name   = replace("${var.env}-${var.project_name}-${var.name}-policy", "_", "-")
  policy = file(var.file_path)
}
