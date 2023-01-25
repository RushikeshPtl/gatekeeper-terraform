locals {
  policy_file_path      = "${get_terragrunt_dir()}/policy.json"
  role_policy_file_path = "${get_terragrunt_dir()}/role_policy.json"
  definition_file_path  = "${get_terragrunt_dir()}/definition.json"
}

terraform {
  source = "../../../..//modules/state_machine"
}

dependency "find_patient_details" {
  config_path = "../../sm_functions/find_patient_details"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "lookup_responsible_party" {
  config_path = "../../sm_functions/lookup_responsible_party"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "add_responsible_party" {
  config_path = "../../sm_functions/add_responsible_party"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "add_patient" {
  config_path = "../../sm_functions/add_patient"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "add_note_for_patient" {
  config_path = "../../sm_functions/add_note_for_patient"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "add_referral_for_patient" {
  config_path = "../../sm_functions/add_referral_for_patient"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

dependency "add_note_to_referral" {
  config_path = "../../sm_functions/add_note_to_referral"

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

dependency "log_request_error" {
  config_path = "../../sm_functions/log_request_error"

  mock_outputs_allowed_terraform_commands = ["init", "fmt", "validate", "plan", "show"]
  mock_outputs_merge_strategy_with_state  = "shallow"
  mock_outputs = {
    invoke_arn    = "test"
    resource_arn  = "test"
  }
}

inputs = {
    name                   = "AddReferralToAmd"
    policy_file_path       = local.policy_file_path
    role_file_path         = local.role_policy_file_path
    template_file_path     = local.definition_file_path
    template_vars          = {
        "FindPatientDetailsOnAMDArn"     = "${dependency.find_patient_details.outputs.resource_arn}",
        "LookupResponsiblePartyArn"          = "${dependency.lookup_responsible_party.outputs.resource_arn}",
        "AddNoteToPatientArn"            = "${dependency.add_note_for_patient.outputs.resource_arn}",
        "AddResponsiblePartyArn"           = "${dependency.add_responsible_party.outputs.resource_arn}",
        "AddPatientArn"            = "${dependency.add_patient.outputs.resource_arn}",
        "AddReferralsForPatientArn"        = "${dependency.add_referral_for_patient.outputs.resource_arn}",
        "SendFallbackResponseArn"   = "${dependency.send_fallback_response.outputs.resource_arn}",
        "LogRequestError"    = "${dependency.log_request_error.outputs.resource_arn}",
        "AddReferralNoteArn"   = "${dependency.add_note_to_referral.outputs.resource_arn}"
    },
    function_arns           = [
        dependency.find_patient_details.outputs.resource_arn,
        dependency.lookup_responsible_party.outputs.resource_arn,
        dependency.add_responsible_party.outputs.resource_arn,
        dependency.add_patient.outputs.resource_arn,
        dependency.add_note_for_patient.outputs.resource_arn,
        dependency.add_referral_for_patient.outputs.resource_arn,
        dependency.add_note_to_referral.outputs.resource_arn,
        dependency.log_request_error.outputs.resource_arn,
        dependency.send_fallback_response.outputs.resource_arn
    ]
}

include {
  path = find_in_parent_folders()
}