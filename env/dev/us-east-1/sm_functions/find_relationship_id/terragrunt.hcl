locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../../..//modules/lambda"
}

inputs = {
  lambda_relative_path = "/../../"
  function_name        = "find_relationship_id"
  module_name          = "sm_functions"
  handler              = "app.lambda_handler"
  runtime              = "python3.9"
  memory_size          = 128
  warmup_enabled       = true
  schedule             = "rate(5 minutes)"
  env                  = "${local.env_vars.locals.env}"
  project_name         = "${local.env_vars.locals.project_name}"
  environment_variables = {
    "Region"          = "us-east-1"
  }
}

include {
  path = find_in_parent_folders()
}