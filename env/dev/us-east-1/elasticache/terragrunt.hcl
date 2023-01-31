locals {
  env_vars          = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../..//modules/elasticache"
}

inputs = {
    username = "${local.env_vars.locals.env}-cache-user"
    usergroup = "${local.env_vars.locals.env}-cache-user-group"
}
