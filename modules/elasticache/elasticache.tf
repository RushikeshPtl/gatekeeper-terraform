data "aws_secretsmanager_random_password" "elasticache_password" {
    password_length = 30
    exclude_punctuation = true
}

resource "aws_secretsmanager_secret" "elasticache_secret" {
    name = "elasticache-secret"
}

resource "aws_secretsmanager_secret_version" "elasticache_secret_version" {
    secret_id     = aws_secretsmanager_secret.elasticache_secret.id
    secret_string = jsonencode({
        "username": var.username,
        "password": data.aws_secretsmanager_random_password.elasticache_password.random_password
    })
}

resource "aws_elasticache_user" "elasticache_user" {
    user_id       = var.username
    user_name     = var.username
    access_string = "on ~* +@all"
    engine        = "REDIS"
    passwords     = [data.aws_secretsmanager_random_password.elasticache_password.random_password]
}

resource "aws_elasticache_user_group" "elasticache_user_group" {
    engine        = "REDIS"
    user_group_id = var.usergroup
    user_ids      = ["default", aws_elasticache_user.elasticache_user.user_id]
}

resource "aws_elasticache_subnet_group" "elasticache_subnet" {
    name        = "elasticache-subnet"
    description = "Elasticache subnet group"
    subnet_ids  = var.subnet_ids
}

resource "aws_elasticache_replication_group" "elasticache_replication_group" {
    description                 = "Cache for properties"
    at_rest_encryption_enabled  = true
    automatic_failover_enabled  = true
    engine                      = "REDIS"
    engine_version              = "6.2"
    replication_group_id        = "elasticache-rep-group"
    node_type                   = "cache.t3.small"
    replicas_per_node_group     = 2
    parameter_group_name        = "default.redis6.x"
    port                        = 6379
    security_group_ids          = var.security_group_ids
    subnet_group_name           = aws_elasticache_subnet_group.elasticache_subnet.name
    multi_az_enabled            = true
    transit_encryption_enabled  = true
    user_group_ids              = [aws_elasticache_user_group.elasticache_user_group.id]
}