variable "template_file_path" {
  description = "The path to step function template"
  type        = string
}

variable "template_vars" {
  description = "Variables for interpolation within the template"
  type        = map(string)
  default     = {}
}

variable "function_arns" {
  description = "Variables for interpolation within the template"
  type        = list(string)
  default     = []
}

variable "type" {
  description = "Determines whether a Standard or Express state machine is created"
  type        = string
  default     = "STANDARD"
}

variable "name" {
  description = "The name of the state machine."
  type        = string
}

variable "role_file_path" {
  description = "Path to role file"
  type        = string
}


variable "policy_file_path" {
  description = "Path to policy file"
  type        = string
}
