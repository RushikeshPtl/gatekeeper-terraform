locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../..//modules/elasticache"
}

inputs = {
  user_id            = "devcacheuserid"
  user_name          = "devcacheuser"
  user_group_id      = "devcacheusergroup"
  subnet_ids         = local.env_vars.locals.subnet_ids
  security_group_ids = local.env_vars.locals.security_group_ids
}

include {
  path = find_in_parent_folders()
}
