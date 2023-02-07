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
    config_path = "../../stream_zip_code_policy"
    mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
    mock_outputs_merge_strategy_with_state  = "shallow"
    mock_outputs = {
    arn  = "1234567890"
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

dependency "zip_codes_table" {
  config_path = "../../zip_code_table"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    arn  = "1234567890"
    stream_arn  = "1234567890_arn"
  }
}

dependency "elasticache" {
  config_path = "../../elasticache_replication_group"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    elasticache_endpoint_address  = "1234567890"
  }
}

inputs = {
  lambda_relative_path = "/../../"
  function_name        = "stream_zip_codes"
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
    "REDIS_HOST"        =  dependency.elasticache.outputs.elasticache_endpoint_address
    "REDIS_PORT"        =  6379
    "GET_SECRET_ARN"    = dependency.get_secrets.outputs.resource_arn
  }
  layers = [
    dependency.shared_layer.outputs.layer_arn,
    dependency.packages_layer.outputs.layer_arn
  ]
  event_source_arns = [
    dependency.zip_codes_table.outputs.stream_arn
  ]
}

include {
  path = find_in_parent_folders()
}
