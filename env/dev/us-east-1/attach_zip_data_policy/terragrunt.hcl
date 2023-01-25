locals {
  env_vars          = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
  policy_file_path  = "${get_terragrunt_dir()}/policy.json"
}

terraform {
  source = "../../../..//modules/policy"
}

inputs = {
  name          = "${local.env_vars.locals.env}-AttachZipDynamoPolicy"
  file_path     = local.policy_file_path
}

include {
  path = find_in_parent_folders()
}
