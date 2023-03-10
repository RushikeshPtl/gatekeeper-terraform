import json
import boto3

def lambda_handler(event, context):
    """
        Function Name: "ValidateDOB"

        - Validates ssn recieved for both client & responsible party
        - Looks for missing value also confirms that input value only includes integers.
        - Adds description in validation_check dictionary in case of failed validation.

        Parameters:
        -------
        event: dict

        Returns:
        -------
        dict: With validation checks & generic json.

    """
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    try:
        generic_json = event["generic_json"]
        validation_check = event["validation_checks"]
        client = generic_json["client"]
        responsible = generic_json["responsible_party"]
        request_id = event.get("request_id", None)
        validation_check["ssn"] = []
        if "ssn" not in client.keys() or not client["ssn"] or sum(not chr.isspace() for chr in client["ssn"]) < 1:
            validation_check["ssn"].append("Missing client ssn")
        elif not all(str.isdigit(char) for char in client["ssn"]):
            validation_check["ssn"].append("Invalid client ssn")
        if responsible:
            if "ssn" not in responsible.keys() or not responsible["ssn"] or sum(not chr.isspace() for chr in responsible["ssn"]) < 1:
                validation_check["ssn"].append("Missing responsible ssn")
            elif not all(str.isdigit(char) for char in responsible["ssn"]):
                validation_check["ssn"].append("Invalid responsible ssn")
        if validation_check["ssn"] == []:
            del validation_check["ssn"]

        return {
                "status" : 200,
                "msg" : "SSN Validation Completed",
                "validation_checks" : validation_check,
                "original_request" : event["original_request"],
                "generic_json" : generic_json,
                "request_id" : request_id
            }
    except Exception as e:
        return {
                "request_id": event.get("request_id", None),
                "payload": event.get("generic_json", {}),
                "is_validate": "failed",
                "error_reason": "Rererral ssn vallidation failed [PATH: /validate_referral/validate_ssn]",
                "error_exception": str(e),
                "msg": "Log Error",
            }
