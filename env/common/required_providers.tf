terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "4.52.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "3.4.3"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "2.3.0"
    }
  }
}
