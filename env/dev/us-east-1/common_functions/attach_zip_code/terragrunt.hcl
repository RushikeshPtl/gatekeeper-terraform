locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../../..//modules/lambda"
}


dependency "packages_layer" {
  config_path = "../../packages_layer"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    layer_arn = ""
  }
}

dependency "shared_layer" {
  config_path = "../../shared_layer"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    layer_arn = ""
  }
}

dependency "custom_policy" {
    config_path = "../../attach_zip_data_policy"
    mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
    mock_outputs_merge_strategy_with_state  = "shallow"
    mock_outputs = {
    arn  = "1234567890"
  }
}

inputs = {
  lambda_relative_path = "/../../"
  function_name        = "attach_zip_code"
  module_name          = "common_functions"
  handler              = "app.lambda_handler"
  runtime              = "python3.9"
  memory_size          = 128
  env                  = "${local.env_vars.locals.env}"
  project_name         = "${local.env_vars.locals.project_name}"
  policies = [
    dependency.custom_policy.outputs.arn
  ]
  environment_variables = {
    "STAGE_BUCKET_NAME" =  "hh-stage-gatekeeper-utilities"
    "PROD_BUCKET_NAME"  =  "hh-prod-gatekeeper-utilities"
    "KEY"               = "zipcodes.json"
    "ENVIRONMENT"       = "${local.env_vars.locals.env}"
  }
  layers = [
    dependency.shared_layer.outputs.layer_arn,
    dependency.packages_layer.outputs.layer_arn
  ]
}

include {
  path = find_in_parent_folders()
}
