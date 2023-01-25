locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../../..//modules/lambda"
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

dependency "update_s3" {
  config_path = "../update_s3"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    function_name = "test"
  }
}

inputs = {
  lambda_relative_path = "/../../"
  function_name        = "get_user_from_session"
  module_name          = "dashboard_functions"
  handler              = "app.lambda_handler"
  runtime              = "python3.9"
  memory_size          = 128
  warmup_enabled       = true
  schedule             = "rate(5 minutes)"
  env                  = "${local.env_vars.locals.env}"
  project_name         = "${local.env_vars.locals.project_name}"
  policies = [
    "arn:aws:iam::${dependency.caller_identity.outputs.account_id}:policy/InvokeGetSecrets",
    "arn:aws:iam::${dependency.caller_identity.outputs.account_id}:policy/Lambda-S3-Access",
  ]
  environment_variables = {
    "STAGE_S3_BUCKET"= "hh-gatekeeper-stage-identity-pool"
    "PROD_S3_BUCKET" = "hh-gatekeeper-production-identity-pool"
    "UPDATE_S3_ARN"  = dependency.update_s3.outputs.invoke_arn
  }
}

include {
  path = find_in_parent_folders()
}
