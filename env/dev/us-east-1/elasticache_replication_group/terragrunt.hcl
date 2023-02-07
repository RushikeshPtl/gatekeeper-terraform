locals {
  env_vars          = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../..//modules/elasticache"
}

dependency "user" {
  config_path = "../elasticache_user"
  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    user_id  = "1234567890"
  }
}

inputs = {
    replication_group_name = "${local.env_vars.locals.env}-gatekeeper-replication-group"
    user_id                = dependency.user.outputs.user_id
    usergroup              = "${local.env_vars.locals.env}-gatekeeper-user-group"
}

include {
  path = find_in_parent_folders()
}