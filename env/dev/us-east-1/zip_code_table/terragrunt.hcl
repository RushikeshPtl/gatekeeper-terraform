locals {
  env_vars          = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../..//modules/dynamodb_table"
}

inputs = {
    table_name      = "${local.env_vars.locals.env}-ZipCodes"
    partition_key   = "Identifier"
    read_capacity   = 2000
    write_capacity  = 2000
}
