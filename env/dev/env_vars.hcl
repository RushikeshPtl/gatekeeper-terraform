locals {
  env                = "dev"
  project_name       = "gatekeeper"
  state_bucket       = "dev-gatekeeper-lambda-tfstate"
  state_lock_table   = "dev-gatekeeper-lambda-infra-state-lock"
  subnet_ids         = ["subnet-061584d93b51d2b7c", "subnet-02631b97d1a2f5b62"]
  security_group_ids = ["sg-081946533c970c401"]
}
