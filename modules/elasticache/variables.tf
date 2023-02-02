variable "user_id" {
    description = "ID for elasticache user"
    type        = string
}
variable "user_name" {
    description = "Name for elasticache user"
    type        = string
}

variable "user_group_id" {
    description = "Name of elasticache user group"
    type        = string
}

variable "subnet_ids" {
  description = "VPC subnet ids"
  type        = list(string)
}

variable "security_group_ids" {
  description = "VPC Security Group"
  type        = list(string)
}
