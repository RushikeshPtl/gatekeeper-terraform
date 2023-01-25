locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../..//modules/lambda_layer_version"
}

# dependency "buckets" {
#   config_path = "../buckets"

#   mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
#   mock_outputs_merge_strategy_with_state  = "shallow"
#   mock_outputs = {
#     lambda_bucket_id = "test"
#   }
# }

inputs = {
  source_code_relative_path = "/../../"
  # lambda_bucket_id          = dependency.buckets.outputs.lambda_bucket_id
  layer_name                = "deployment_environment"
  compatible_runtimes       = ["python3.9"]
  path                      = "src/packages/"
  env                       = "${local.env_vars.locals.env}"
  project_name              = "${local.env_vars.locals.project_name}"
}

include {
  path = find_in_parent_folders()
}