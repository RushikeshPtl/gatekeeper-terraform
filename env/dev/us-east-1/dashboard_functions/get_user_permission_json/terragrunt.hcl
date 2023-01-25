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

dependency "caller_identity" {
    config_path = "../../caller_identity"

    mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
    mock_outputs_merge_strategy_with_state  = "shallow"
    mock_outputs = {
        account_id  = "1234567890"
        caller_arn  = "1234567890_arn"
        caller_user = "1234567890_user"
    }
}

dependency "get_user_from_session" {
    config_path = "../get_user_from_session"
    mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
    mock_outputs_merge_strategy_with_state  = "shallow"
    mock_outputs = {
        invoke_arn    = "test"
        function_name = "test"
    }
}

inputs = {
    lambda_relative_path = "/../../"
    function_name        = "get_user_permission_json"
    module_name          = "dashboard_functions"
    handler              = "app.lambda_handler"
    runtime              = "python3.9"
    memory_size          = 128
    warmup_enabled       = true
    include_vpc          = true
    schedule             = "rate(5 minutes)"
    env                  = "${local.env_vars.locals.env}"
    project_name         = "${local.env_vars.locals.project_name}"
    policies = [
        "arn:aws:iam::${dependency.caller_identity.outputs.account_id}:policy/InvokeGetSecrets"
    ]
    environment_variables = {
        "GET_USER_ARN"    = dependency.get_user_from_session.outputs.invoke_arn
    }
    layers = [
        dependency.shared_layer.outputs.layer_arn,
        dependency.packages_layer.outputs.layer_arn
    ]
    apigateway_id            = dependency.apigateway.outputs.api_id
    apigateway_execution_arn = dependency.apigateway.outputs.execution_arn
    api_paths = [
        {
            "method" = "GET",
            "path"   = "/permissions/get-user-permisson-json"
        }
    ]
}

include {
    path = find_in_parent_folders()
}
