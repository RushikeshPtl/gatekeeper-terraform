
output "status" {
  description = "ARN of Lambda Function"
  value       = aws_sfn_state_machine.sfn_state_machine.status
}
