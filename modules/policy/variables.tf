variable "name" {
  description = "Name of role"
  type        = string
}

variable "file_path" {
  description = "Path to policy file"
  type        = string
}

variable "template_vars" {
  description = "Variables for policy json"
  type        = map(string)
  default     = {}
}

