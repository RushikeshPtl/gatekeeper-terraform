
resource "aws_secretsmanager_secret" "elasticache_secret" {
  name_prefix = replace("${var.env}-${var.project_name}-elasticache-secret", "_", "-")
}

resource "aws_secretsmanager_secret_version" "elasticache_secret_version" {
  secret_id = aws_secretsmanager_secret.elasticache_secret.id
  secret_string = jsonencode({
    "username" : var.user_name,
    "password" : var.password
  })
}

resource "aws_elasticache_user" "elasticache_user" {
  user_id       = var.user_id
  user_name     = var.user_name
  access_string = "on ~* +@all"
  engine        = "REDIS"
  passwords     = [var.password]
}

resource "aws_elasticache_user_group" "elasticache_user_group" {
  engine        = "REDIS"
  user_group_id = var.user_group_id
  user_ids      = ["default", aws_elasticache_user.elasticache_user.user_id]
}

resource "aws_elasticache_subnet_group" "elasticache_subnet" {
  name        = replace("${var.env}-${var.project_name}-elasticache-subnet", "_", "-")
  description = "Elasticache subnet group"
  subnet_ids  = var.subnet_ids
}

resource "aws_elasticache_replication_group" "elasticache_replication_group" {
  description                = "Cache for properties"
  at_rest_encryption_enabled = true
  automatic_failover_enabled = true
  engine                     = "redis"
  engine_version             = "6.2"
  replication_group_id       = replace("${var.env}-${var.project_name}-elasticache-rep-group", "_", "-")
  node_type                  = "cache.t3.small"
  replicas_per_node_group    = 2
  parameter_group_name       = "default.redis6.x"
  port                       = 6379
  security_group_ids         = var.security_group_ids
  subnet_group_name          = aws_elasticache_subnet_group.elasticache_subnet.name
  multi_az_enabled           = true
  transit_encryption_enabled = true
  user_group_ids             = [aws_elasticache_user_group.elasticache_user_group.id]
}
