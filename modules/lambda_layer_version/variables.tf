variable "lambda_bucket_id" {
  description = "Name of the bucket to put the file in"
  type        = string
}

variable "layer_name" {
  description = "Unique name for your Lambda Layer"
  type        = string
}

variable "compatible_runtimes" {
  description = "List of Runtimes this layer is compatible with"
  type        = list(string)
  default     = ["python3.9"]
}

variable "source_code_relative_path" {
  description = "The path to content to the archive "
  type        = string
}

variable "path" {
  description = "The path to content to the archive"
  type        = string
}
