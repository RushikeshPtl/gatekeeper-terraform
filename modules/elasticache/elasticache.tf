resource "aws_elasticache_user_group" "elasticache_user_group" {
    engine        = "REDIS"
    user_group_id = var.usergroup
    user_ids      = ["default", "${var.user_id}"]
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
    replication_group_id        = var.replication_group_name
    node_type                   = "cache.t3.small"
    replicas_per_node_group     = 2
    parameter_group_name        = "default.redis6.x"
    port                        = 6379
    security_group_ids          = var.security_group_ids
    subnet_group_name           = aws_elasticache_subnet_group.elasticache_subnet.name
    multi_az_enabled            = true
    transit_encryption_enabled  = true
    user_group_ids              = [aws_elasticache_user_group.elasticache_user_group.id]
    timeouts {
        update = "20m"
    }
}