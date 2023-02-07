data "aws_secretsmanager_random_password" "elasticache_password" {
    password_length = 30
    exclude_punctuation = true
}

resource "aws_secretsmanager_secret" "elasticache_secret" {
    name = "${var.username}-password"
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