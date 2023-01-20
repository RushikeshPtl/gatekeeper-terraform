resource "aws_iam_policy" "policy" {
  name   = "${var.env}-${var.project_name}-${var.name}-policy"
  policy = file(var.file_path)
}
