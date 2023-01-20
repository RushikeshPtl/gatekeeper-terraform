locals {
  env              = "dev"
  project_name     = "gatekeeper"
  state_bucket     = "dev-gatekeeper-lambda-tfstate"
  state_lock_table = "dev-gatekeeper-lambda-infra-state-lock"
}
