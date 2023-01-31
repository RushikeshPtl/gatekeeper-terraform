variable "username" {
    description = "Name for elasticache user"
    type        = string
}

variable "usergroup" {
    description = "Name of elasticache user group"
    type        = string
}

variable "subnet_ids" {
  description = "VPC subnet ids"
  type        = list(string)
  default     = ["subnet-061584d93b51d2b7c", "subnet-02631b97d1a2f5b62"]
}

variable "security_group_ids" {
  description = "VPC Security Group"
  type        = list(string)
  default     = ["sg-081946533c970c401"]
}