variable "table_name" {
    description = "Name of table"
    type        = string
}

variable "partition_key" {
    description = "Partition key"
    type        = string
}

variable "read_capacity" {
    description = "Read capacity for table"
    type        = number
}

variable "write_capacity" {
    description = "Write capacity for table"
    type        = number
}
