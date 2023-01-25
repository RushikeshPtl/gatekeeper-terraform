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

dependency "get_secrets" {
  config_path = "../get_secrets"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    function_name = "test"
  }
}

inputs = {
  lambda_relative_path = "/../../"
  function_name        = "update_database"
  module_name          = "common_functions"
  handler              = "app.lambda_handler"
  runtime              = "python3.9"
  memory_size          = 128
  env                  = "${local.env_vars.locals.env}"
  project_name         = "${local.env_vars.locals.project_name}"
  policies = [
    "arn:aws:iam::${dependency.caller_identity.outputs.account_id}:policy/InvokeGetSecrets",
    "arn:aws:iam::${dependency.caller_identity.outputs.account_id}:policy/RdsReadWriteAccess",
    "arn:aws:iam::${dependency.caller_identity.outputs.account_id}:policy/EC2Access"
  ]
  environment_variables = {
    "GET_SECRET_ARN"        =  dependency.get_secrets.outputs.invoke_arn
  }
  layers = [
    dependency.shared_layer.outputs.layer_arn,
    dependency.packages_layer.outputs.layer_arn
  ]
}

include {
  path = find_in_parent_folders()
}
