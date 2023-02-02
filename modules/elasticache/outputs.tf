output "elasticache_endpoint_address" {
  description = "Address of the endpoint for the primary node in the replication group"
  value       = aws_elasticache_replication_group.elasticache_replication_group.primary_endpoint_address
}

output "password" {
  value = data.aws_secretsmanager_random_password.elasticache_password.random_password
}
