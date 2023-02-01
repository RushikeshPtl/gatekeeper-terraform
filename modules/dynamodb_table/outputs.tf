output "arn" {
    description = "Arn of dynamo db table"
    value       = aws_dynamodb_table.zip_codes_table.arn 
}

output "stream_arn" {
    description = "Stream Arn of dynamo db table"
    value       = aws_dynamodb_table.zip_codes_table.stream_arn 
}