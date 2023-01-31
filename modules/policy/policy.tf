resource "aws_iam_policy" "policy" {
  name   = replace("${var.env}-${var.project_name}-${var.name}-policy", "_", "-")
  policy = templatefile(var.file_path, var.template_vars)
}
