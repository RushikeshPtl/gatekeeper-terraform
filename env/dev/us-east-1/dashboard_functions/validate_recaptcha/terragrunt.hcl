locals {
  env_vars = read_terragrunt_config(find_in_parent_folders("env_vars.hcl"))
}

terraform {
  source = "../../../../..//modules/lambda"
}


dependency "packages_layer" {
    config_path = "../../packages_layer"

    mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
    mock_outputs_merge_strategy_with_state  = "shallow"
    mock_outputs = {
        layer_arn = ""
    }
}

dependency "shared_layer" {
    config_path = "../../shared_layer"

    mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
    mock_outputs_merge_strategy_with_state  = "shallow"
    mock_outputs = {
        layer_arn = ""
    }
}

dependency "apigateway" {
    config_path = "../../apigateway"

    mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
    mock_outputs_merge_strategy_with_state  = "shallow"
    mock_outputs = {
        api_id        = "test"
        execution_arn = "arn:aws:events:eu-west-1:111122223333:rule/RunDaily"
    }
}

inputs = {
    lambda_relative_path = "/../../"
    function_name        = "validate_recaptcha"
    module_name          = "dashboard_functions"
    handler              = "app.lambda_handler"
    runtime              = "python3.9"
    memory_size          = 128
    warmup_enabled       = true
    schedule             = "rate(5 minutes)"
    env                  = "${local.env_vars.locals.env}"
    project_name         = "${local.env_vars.locals.project_name}"
    environment_variables = {
        "RECAPTCHA_URL"                = "https://www.google.com/recaptcha/api/siteverify"
        "RECAPTCHA_SECRET_KEY"         = "6Le44tUiAAAAAPkBDvKAGzGZMxDEPyGhxsNwO1Mp"
    }
    layers = [
        dependency.shared_layer.outputs.layer_arn,
        dependency.packages_layer.outputs.layer_arn
    ]
    apigateway_id            = dependency.apigateway.outputs.api_id
    apigateway_execution_arn = dependency.apigateway.outputs.execution_arn
    api_paths = [
        {
            "method" = "POST",
            "path"   = "/verify_captcha"
        }
    ]
}

include {
    path = find_in_parent_folders()
}
