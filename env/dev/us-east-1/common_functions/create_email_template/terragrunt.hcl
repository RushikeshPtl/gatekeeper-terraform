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

dependency "caller_identity" {
  config_path = "../../caller_identity"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    account_id  = "1234567890"
    caller_arn  = "1234567890_arn"
    caller_user = "1234567890_user"
  }
}

inputs = {
  lambda_relative_path = "/../../"
  function_name        = "create_email_template"
  module_name          = "common_functions"
  handler              = "app.lambda_handler"
  runtime              = "python3.9"
  memory_size          = 128
  env                  = "${local.env_vars.locals.env}"
  project_name         = "${local.env_vars.locals.project_name}"
  policies = [
    "arn:aws:iam::${dependency.caller_identity.outputs.account_id}:policy/SendEmailPolicy"
  ]
  environment_variables = {
    "ENVIRONMENT" = "${local.env_vars.locals.env}"
  }
  layers = [
    dependency.shared_layer.outputs.layer_arn,
    dependency.packages_layer.outputs.layer_arn
  ]
}

include {
  path = find_in_parent_folders()
}
