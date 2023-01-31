resource "aws_dynamodb_table" "zip_codes_table" {
    name             = var.table_name
    hash_key         = var.partition_key
    billing_mode     = "PROVISIONED"
    stream_enabled   = true
    stream_view_type = "NEW_AND_OLD_IMAGES"
    read_capacity    = var.read_capacity
    write_capacity   = var.write_capacity
    attribute {
        name = var.partition_key
        type = "S"
    }
}