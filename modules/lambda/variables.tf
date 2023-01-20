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

variable "api_paths" {
  type = list(object({
    method = string
    path   = string
  }))

  default = [
  ]
}

variable "apigateway_id" {
  description = "URI of the Lambda function for a Lambda proxy integration."
  type        = string
  default     = null
}

variable "apigateway_execution_arn" {
  description = "The output of the archive file."
  type        = string
  default     = null
}

