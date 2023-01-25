locals {
  policy_file_path      = "${get_terragrunt_dir()}/policy.json"
  role_policy_file_path = "${get_terragrunt_dir()}/role_policy.json"
  definition_file_path  = "${get_terragrunt_dir()}/definition.json"
}

terraform {
  source = "../../../..//modules/state_machine"
}

dependency "convert" {
  config_path = "../../sm_functions/convert"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "validate_token" {
  config_path = "../../sm_functions/validate_token"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "validate_name" {
  config_path = "../../sm_functions/validate_name"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "validate_dob" {
  config_path = "../../sm_functions/validate_dob"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "validate_ssn" {
  config_path = "../../sm_functions/validate_ssn"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "validate_general" {
  config_path = "../../sm_functions/validate_general"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "log_request_error" {
  config_path = "../../sm_functions/log_request_error"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "find_duplicate_request" {
  config_path = "../../sm_functions/find_duplicate_request"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "save_referral_request" {
  config_path = "../../sm_functions/save_referral_request"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "send_fallback_response" {
  config_path = "../../sm_functions/send_fallback_response"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

inputs = {
    name                   = "ValidateReferral"
    policy_file_path       = local.policy_file_path
    role_file_path         = local.role_policy_file_path
    template_file_path     = local.definition_file_path
    template_vars          = {
        "ConvertUFTReferralArn"     = "${dependency.convert.outputs.resource_arn}",
        "ValidateTokenArn"          = "${dependency.validate_token.outputs.resource_arn}",
        "ValidateDOBArn"            = "${dependency.validate_dob.outputs.resource_arn}",
        "ValidateNameArn"           = "${dependency.validate_name.outputs.resource_arn}",
        "ValidateSSNArn"            = "${dependency.validate_ssn.outputs.resource_arn}",
        "ValidateGeneralArn"        = "${dependency.validate_general.outputs.resource_arn}",
        "FindDuplicateRequestArn"   = "${dependency.find_duplicate_request.outputs.resource_arn}",
        "SaveReferralRequestArn"    = "${dependency.save_referral_request.outputs.resource_arn}",
        "SendFallbackResponseArn"   = "${dependency.send_fallback_response.outputs.resource_arn}"
    },
    function_arns           = [
        dependency.convert.outputs.resource_arn,
        dependency.validate_token.outputs.resource_arn,
        dependency.validate_dob.outputs.resource_arn,
        dependency.validate_name.outputs.resource_arn,
        dependency.validate_ssn.outputs.resource_arn,
        dependency.validate_general.outputs.resource_arn,
        dependency.find_duplicate_request.outputs.resource_arn,
        dependency.save_referral_request.outputs.resource_arn,
        dependency.send_fallback_response.outputs.resource_arn
    ]
}

include {
  path = find_in_parent_folders()
}