locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../..//modules/lambda"
}

dependency "buckets" {
  config_path = "../buckets"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    lambda_bucket_id = "test"
  }
}

dependency "packages_layer" {
  config_path = "../packages_layer"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    layer_arn = ""
  }
}

dependency "shared_layer" {
  config_path = "../shared_layer"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    layer_arn = ""
  }
}

inputs = {
  lambda_relative_path = "/../../"
  lambda_bucket_id     = dependency.buckets.outputs.lambda_bucket_id
  function_name        = "get_secrets"
  handler              = "get_secrets.lambda_handler"
  runtime              = "python3.9"
  memory_size          = 256
  warmup_enabled       = true
  schedule             = "rate(5 minutes)"
  env                  = "${local.env_vars.locals.env}"
  project_name         = "${local.env_vars.locals.project_name}"
  policies = [
    "arn:aws:iam::aws:policy/SecretsManagerReadWrite"
  ]
  environment_variables = {
    "REGION_NAME"          = "us-east-1",
    "DATABASE_SECRET_NAME" = "stage/gatekeeper/rds/admin",
    "DATABASE_ENDPOINT"    = "hh-microservice-db.cou4r3yvy2cs.us-east-1.rds.amazonaws.com",
    "DATABASE_NAME"        = "postgres",
    "AMD_SECRET_NAME"      = "amd/token/DEV",
    "AMD_CREDS_NAME"       = "amd/creds/DEV"
    "UFT_TOKEN"            = "uft/stage",
    "REDIS_CREDS_NAME"     = "ElastiCacheCreds",
  }
  layers = [
    dependency.shared_layer.outputs.layer_arn,
    dependency.packages_layer.outputs.layer_arn
  ]
}

include {
  path = find_in_parent_folders()
}
