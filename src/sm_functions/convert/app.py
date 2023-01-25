import json


def lambda_handler(event, context):
    """
        Function Name : ConvertUFTReferral

        Converts request data into generic json which will be frthered validated & used to save the referral.

        Parameters:
        -------
        event: dict

        Response:
        -------
        dict: having original request along with converted generic json

    """
    if not isinstance(event, dict):
        event = json.loads(event)
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    client = {}
    responsible = {}
    provider = {}
    request_id = event.get("request_id", None)
    token = event.get("token", "")
    validation_check = {}
    if "dependents" in event.keys() and event["dependents"] and isinstance(event["dependents"], list) and len(event["dependents"]) > 0 and event["dependents"][0]:
        dependant = event["dependents"][0]
        client["lastname"] = dependant.get("account_lastname", "")
        client["firstname"] = dependant.get("account_firstname", "")
        client["middle_initial"] = dependant.get("account_middle_initial", "")
        client["dob"] = dependant.get("dob", "")
        client["ssn"] = dependant.get("ssn", "")
        client["email"] = dependant.get("email", "")
        client["gender"] = dependant.get("gender", "")
        client["referral_type"] = dependant.get("referral_type", "")
        client["relation"] = dependant.get("relationship_to_member", "")
        client["case_number"] = event["member_fields"].get("case_number", "") if "member_fields" in event.keys() else ""
        client["external_id"] = (
            dependant["uft_id"]
            if "uft_id" in dependant.keys() and dependant["uft_id"] and dependant["uft_id"].strip()
            else event["member_fields"].get("uft_id", "") if "member_fields" in event.keys() else ""
        )
        client["phone"] = dependant.get("phone", "")
        client["mobile_phone"] = dependant.get("mobile", "")
        client["address1"] = dependant.get("address1", "")
        client["address2"] = dependant.get("address2", "")
        client["city"] = dependant.get("city", "")
        client["state"] = dependant.get("state", "")
        client["zip"] = dependant.get("zip", "")
        if "member_fields" in event.keys():
            member_data = event["member_fields"]
            responsible["lastname"] = member_data.get("account_lastname", "")
            responsible["firstname"] = member_data.get("account_firstname", "")
            responsible["middle_initial"] = member_data.get(
                "account_middle_initial", ""
            )
            responsible["ssn"] = member_data.get("ssn", "")
            responsible["dob"] = member_data.get("dob", "")
            responsible["email"] = member_data.get("email", "")
            responsible["gender"] = member_data.get("gender", "")
            responsible["employment_status"] = member_data.get("employment_status", "")
            responsible["referral_reason"] = member_data.get("referral_reason", "")
            responsible["phone"] = member_data.get("phone", "")
            responsible["mobile_phone"] = member_data.get("mobile", "")
            responsible["external_id"] = member_data.get("uft_id", "")
            responsible["address1"] = member_data.get("address1", "")
            responsible["address2"] = member_data.get("address2", "")
            responsible["city"] = member_data.get("city", "")
            responsible["state"] = member_data.get("state", "")
            responsible["zip"] = member_data.get("zip", "")
        else:
            validation_check = {"Member" : ["Member data not present"]}
            member_data = {}
    else:
        if "member_fields" in event.keys():
            client_data = event["member_fields"]
            client["firstname"] = client_data.get("account_firstname", "")
            client["lastname"] = client_data.get("account_lastname", "")
            client["middle_initial"] = client_data.get("account_middle_initial", "")
            client["ssn"] = client_data.get("ssn", "")
            client["dob"] = client_data.get("dob", "")
            client["email"] = client_data.get("email", "")
            client["gender"] = client_data.get("gender", "")
            client["employment_status"] = client_data.get("employment_status")
            client["referral_type"] = client_data.get("referral_type", "")
            client["referral_reason"] = client_data.get("referral_reason", "")
            client["case_number"] = client_data.get("case_number", "")
            client["phone"] = client_data.get("phone", "")
            client["mobile_phone"] = client_data.get("mobile", "")
            client["external_id"] = client_data.get("uft_id", "")
            client["address1"] = client_data.get("address1", "")
            client["address2"] = client_data.get("address2", "")
            client["city"] = client_data.get("city", "")
            client["state"] = client_data.get("state", "")
            client["zip"] = client_data.get("zip", "")
    if "referring_counselor" in event.keys():
        referring_counselor = event["referring_counselor"]
        provider["email"] = referring_counselor.get("email", "")
        provider["phone"] = referring_counselor.get("phone", "")
        first_name = referring_counselor["account_firstname"] if "account_firstname" in referring_counselor and referring_counselor["account_firstname"] else ""
        last_name = referring_counselor["account_lastname"] if "account_lastname" in referring_counselor and referring_counselor["account_lastname"] else ""
        provider["name"] = first_name + " " + last_name
        client["note"] = referring_counselor.get("comments", "")
    else:
        referring_counselor = {}

    generic = {
        "token": token,
        "emr": "AMD",
        "client": client,
        "responsible_party": responsible,
        "referring_provider": provider,
    }
    return {
        "statusCode": 200,
        "original_request": event,
        "generic_json": generic,
        "request_id": request_id,
        "validation_checks" : validation_check
        }
