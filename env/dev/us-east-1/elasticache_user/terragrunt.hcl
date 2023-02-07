locals {
  env_vars          = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../..//modules/elasticache_user"
}

inputs = {
    username               = "${local.env_vars.locals.env}-gatekeeper-user"
}

include {
  path = find_in_parent_folders()
}