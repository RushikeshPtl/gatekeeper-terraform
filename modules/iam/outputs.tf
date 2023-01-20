output "exec_role_arn" {
  description = "Amazon Resource Name (ARN) specifying the role."
  value       = aws_iam_role.role.arn
}
