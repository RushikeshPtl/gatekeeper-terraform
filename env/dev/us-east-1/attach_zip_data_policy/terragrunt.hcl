locals {
  env_vars          = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
  policy_file_path  = "${get_terragrunt_dir()}/policy.json"
}

terraform {
  source = "../../../..//modules/policy"
}

dependency "zip_codes_table" {
  config_path = "../zip_code_table"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    arn  = "1234567890"
    stream_arn  = "1234567890_arn"
  }
}

inputs = {
  name          = "${local.env_vars.locals.env}-AttachZipDynamoPolicy"
  file_path     = local.policy_file_path
  template_vars = {
    "DynamoDbArn" = "${dependency.zip_codes_table.outputs.arn}"
  }
}

include {
  path = find_in_parent_folders()
}
