import json
import boto3
import os

def lambda_handler(event, context):
    """
        Function Name: "ValidateGeneral"

        Validates the general fields from referral such as phone/mobile_phone, referral_type, relation & external_id etc.

        phone/mobile_phone : Looks for missing phone/mobile_phone or invalid characters such as ($, @ or alphabets etc.) for client.
        referral_type, relation : Looks for missing values for client.
        external_id : Looks for missing value for client & responsible party

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

    # Validation check for phone
    validation_check["phone/mobile"] = []
    if ("phone" not in client.keys() or not client["phone"]) and (
        "mobile_phone" not in client.keys() or not client["mobile_phone"]
    ):
        validation_check["phone/mobile"].append("Missing phone/mobile for client")
    elif (
        client["phone"] and
        not all(str.isdigit(char) or char == "-" or char == "+" for char in client["phone"])
    ) or (
        client["mobile_phone"] and
        not all(str.isdigit(char) or char == "-" or char == "+" for char in client["mobile_phone"])
    ):
        validation_check["phone/mobile"].append("Invalid phone/mobile for client")
    if validation_check["phone/mobile"] == []:
        del validation_check["phone/mobile"]

    # Validation check for referral type
    if "referral_type" not in client.keys() or not client["referral_type"]:
        validation_check["referral_type"] = ["Missing referral type"]

    if ref_type == "uft" and responsible:
        # Validation check for relation
        if "relation" not in client.keys() or not client["relation"]:
            validation_check["relation"] = ["Dependent missing relationship"]

    if ref_type == "uft":
        # Validation check for external id
        validation_check["external_id"] = []
        if "external_id" not in client.keys() or not client["external_id"]:
            validation_check["external_id"].append("Missing external id for client")
        if responsible:
            if (
                "external_id" not in responsible.keys()
                or not responsible["external_id"]
            ):
                validation_check["external_id"].append(
                    "Missing external id for responsible"
                )
        if validation_check["external_id"] == []:
            del validation_check["external_id"]

    return {
            "status" : 200,
            "validation_checks" : validation_check,
            "original_request" : event["original_request"],
            "generic_json" : generic_json,
            "request_id" : request_id
        }