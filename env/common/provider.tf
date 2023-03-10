provider "aws" {
  region     = var.region
  access_key = var.access_key
  secret_key = var.secret_key


  default_tags {
    tags = {
      Env         = var.env
      ProjectName = var.project_name
      ManagedBy   = "Terraform"
    }
  }
}

