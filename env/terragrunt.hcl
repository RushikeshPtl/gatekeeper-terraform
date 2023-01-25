locals {
  env_vars     = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
  account_vars = read_terragrunt_config(find_in_parent_folders("account.hcl"))
  region_vars  = read_terragrunt_config(find_in_parent_folders("region.hcl"))

  # Extract the variables we need for easy access
  aws_access_key_id     = local.account_vars.locals.aws_access_key_id
  aws_secret_access_key = local.account_vars.locals.aws_secret_access_key
  aws_region            = local.region_vars.locals.aws_region

  state_bucket     = local.env_vars.locals.state_bucket
  state_lock_table = local.env_vars.locals.state_lock_table
}

inputs = {
  env          = "${local.env_vars.locals.env}"
  project_name = "${local.env_vars.locals.project_name}"
  region       = "${local.aws_region}"
  access_key   = "${local.aws_access_key_id}"
  secret_key   = "${local.aws_secret_access_key}"
}

generate "common_variables" {
  path      = "common_variables.tf"
  if_exists = "overwrite"
  contents  = file("./common/common_variables.tf")
}

generate "required_providers" {
  path      = "required_providers.tf"
  if_exists = "overwrite"
  contents  = file("./common/required_providers.tf")
}

generate "provider" {
  path      = "provider.tf"
  if_exists = "overwrite"
  contents  = file("./common/provider.tf")
}

# Generate backend block
generate "backend" {
  path      = "backend.tf"
  if_exists = "overwrite_terragrunt"
  contents  = <<EOF
terraform {
  backend "s3" {
    bucket         = "${local.state_bucket}"
    region         = "${local.aws_region}"
    key            = "${path_relative_to_include()}/terraform.tfstate"
    dynamodb_table = "${local.state_lock_table}"
  }
}
EOF
}
