import json
import boto3

def lambda_handler(event, context):
    """
        Function Name: "ValidateName"

        - Validates first_name & last_name recieved for client.
        - Looks for missing value also confirms that input string doesn"t have any digit in it.
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
    responsible = generic_json["responsible_party"]
    client = generic_json["client"]
    request_id = event.get("request_id", None)
    validation_check["name"] = []
    if "firstname" not in client.keys() or not client["firstname"]:
        validation_check["name"].append("Missing firstname for client")
    elif isinstance(client["firstname"], str) and client["firstname"].lower() in ["none", "null"]:
        validation_check["name"].append("Client firstname can't be none/null")
    elif type(client["firstname"]) != str or all(
        str.isdigit(char) for char in client["firstname"]
    ):
        validation_check["name"].append("Client firstname is not a string")
    if "lastname" not in client.keys() or not client["lastname"]:
        validation_check["name"].append("Missing lastname for client")
    elif isinstance(client["lastname"], str) and client["lastname"].lower() in ["none", "null"]:
        validation_check["name"].append("Client lastname can't be none/null")
    elif type(client["lastname"]) != str or all(
        str.isdigit(char) for char in client["lastname"]
    ):
        validation_check["name"].append("Client last name is not a string")

    if responsible:
        if "firstname" not in responsible.keys() or not responsible["firstname"]:
            validation_check["name"].append("Missing firstname for responsible")
        elif isinstance(responsible["firstname"], str) and responsible["firstname"].lower() in ["none", "null"]:
            validation_check["name"].append("Responsible firstname can't be none/null") 
        elif type(responsible["firstname"]) != str or all(
            str.isdigit(char) for char in responsible["firstname"]
        ):
            validation_check["name"].append("Responsible firstname is not a string")
        if "lastname" not in responsible.keys() or not responsible["lastname"]:
            validation_check["name"].append("Missing lastname for responsible")
        elif isinstance(responsible["lastname"], str) and responsible["lastname"].lower() in ["none", "null"]:
            validation_check["name"].append("Responsible lastname can't be none/null")
        elif type(responsible["lastname"]) != str or all(
            str.isdigit(char) for char in responsible["lastname"]
        ):
            validation_check["name"].append("Responsible last name is not a string")
    if validation_check["name"] == []:
        del validation_check["name"]

    return {
            "status" : 200,
            "validation_checks" : validation_check,
            "original_request" : event["original_request"],
            "generic_json" : generic_json,
            "request_id" : request_id
        }
