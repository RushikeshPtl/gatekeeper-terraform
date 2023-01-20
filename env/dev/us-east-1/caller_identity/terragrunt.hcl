locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../..//modules/caller_identity"
}

inputs = {
  env          = "${local.env_vars.locals.env}"
  project_name = "${local.env_vars.locals.project_name}"
}

include {
  path = find_in_parent_folders()
}

