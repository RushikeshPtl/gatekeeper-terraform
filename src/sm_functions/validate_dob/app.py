import json
import boto3
from datetime import datetime

def lambda_handler(event, context):
    """
        Function Name: "ValidateDOB"

        - Validates dob recieved for both client & responsible party.
        - Looks for missing value also confirms that dob is not from the future.
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
    generic_json = event["generic_json"]
    validation_check = event["validation_checks"]
    client = generic_json["client"]
    responsible = generic_json["responsible_party"]
    ref_type=event["original_request"]["referral_provider"]
    request_id = event.get("request_id", None)
    validation_check["dob"] = []
    if "dob" not in client.keys() or not client["dob"]:
        validation_check["dob"].append("Missing dob for client")
    elif datetime.strptime(client["dob"], "%Y-%m-%d") > datetime.now():
        validation_check["dob"].append("Invalid dob of client")
    if ref_type == "uft":
        if responsible:
            if "dob" not in responsible.keys() or not responsible["dob"]:
                validation_check["dob"].append("Missing dob for responsible party")
            elif datetime.strptime(responsible["dob"], "%Y-%m-%d") > datetime.now():
                validation_check["dob"].append("Invalid dob of responsible party")
    if validation_check["dob"] == []:
        del validation_check["dob"]

    return {
            "status" : 200,
            "validation_checks" : validation_check,
            "original_request" : event["original_request"],
            "generic_json" : generic_json,
            "request_id" : request_id
        }