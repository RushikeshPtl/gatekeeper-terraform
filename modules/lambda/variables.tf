variable "lambda_bucket_id" {
  description = "Name of the bucket to put the file in"
  type        = string
}

variable "lambda_relative_path" {
  description = "The path to content to the archive "
  type        = string
}

variable "function_name" {
  description = "Unique name for your Lambda Function."
  type        = string
}

variable "handler" {
  description = "Function entrypoint in your code."
  type        = string
}


variable "runtime" {
  description = " Identifier of the function's runtime."
  type        = string
}

variable "layers" {
  description = "List of Lambda Layer Version ARNs (maximum of 5) to attach to your Lambda Function"
  type        = list(string)
  default     = []
}

variable "environment_variables" {
  description = "Environment variables"
  type        = map(any)
  default     = {}
}

variable "memory_size" {
  description = "Amount of memory in MB your Lambda Function can use at runtime"
  type        = number
  default     = 128
}

variable "timeout" {
  description = "Amount of time your Lambda Function has to run in seconds."
  type        = number
  default     = 30
}

variable "schedule" {
  description = "Schedule value for the event that triggers the warmer lambda."
  type        = string
  default     = "rate(5 minutes)"
}

variable "warmup_enabled" {
  description = "Whether your lambda should be warmed up or not"
  type        = bool
  default     = false
}

variable "policies" {
  description = "Name of project"
  type        = list(string)
  default     = ["arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"]
}
