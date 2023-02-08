import json
import boto3
import os

def lambda_handler(event, context):
    """
        Function Name: "ValidateToken"

        - Validates token recieved from the request.
        - Looks for missing value also confirms that received token is same as the uft token stored in secret.
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
        referral_type = event["original_request"]["referral_provider"]
        ref_token = event["original_request"]["token"]
        client = boto3.client("lambda")
        response = client.invoke(
            FunctionName = os.environ["GET_ORG_TOKEN_ARN"],
            InvocationType = "RequestResponse",
            Payload = json.dumps({"queryStringParameters": {"org_abbr": referral_type, "token": ref_token, "token_type": "referral"}})
        )
        payload = json.load(response["Payload"])
        if "error" in payload:
            return {
                "error_code": 500,
                "msg": "Error while accessing secrets manager",
                "error": payload["error"]
            }
        else:
            org_id = json.loads(payload["body"]).get("org_id", None)
            validation_check = event["validation_checks"]
            request_id = event.get("request_id", None)
            if not org_id:
                validation_check["token"] = ["Invalid token"]
            return {
                "status" : 200,
                "msg" : "Token validation completed",
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
                "error_reason": "Invalid Rrererral token [PATH: /validate_referral/validate_token]",
                "error_exception": str(e),
                "msg": "Log Error",
            }

        

