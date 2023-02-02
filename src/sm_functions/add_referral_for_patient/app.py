import json
import requests
import boto3
from json.decoder import JSONDecodeError
import os
import datetime

lambda_client = boto3.client("lambda")

def get_amd_codes(referral_provider):
    get_codes = lambda_client.invoke(
        FunctionName=os.environ["GET_AMD_CODES_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"input" : referral_provider}),
    )
    get_codes_response = json.load(get_codes["Payload"])
    amd_codes = get_codes_response["codes"]
    return amd_codes

def lambda_handler(event, context):
    """
        Function Name : AddReferralForPatient

        - After adding patient creates referral for patient in AMD
        - For 'Psychiatric and Counseling Services' creates 2 referrals for each.

        Parameters:
        -------
        event : dict with patient id from AMD & generic json

        Response:
        ------
        dict : With status_code, referral_id, patient_id from AMD.

    """
    headers = {"Content-type": "application/json", "Accept": "application/json"}
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"secret_type": "AMD Token"}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        return {
            "error_code": 500,
            "msg": "Log Error",
            "error_type" : "Internal Error",
            "error_details": payload["error"],
            "error_reason": "Error while accessing secrets manager in AddReferral",
            "request_id": event["request_id"]
        }
    else:
        token = payload["token"]
        headers["Authorization"] = "Bearer {}".format(token)
        webserver = payload["webserver"]
        referral_url = webserver.replace("xmlrpc/processrequest.aspx","").replace("processrequest", "api") + "referral/InboundReferrals"
        referral_provider = event["generic_json"]["referral_provider"]
        amd_codes = get_amd_codes(referral_provider)
        payload = {"input": amd_codes["default_referral_status"], "request_id": event["request_id"]}
        status_response = lambda_client.invoke(
            FunctionName=os.environ["GET_REF_STATUS_ARN"],
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
        status_data = json.load(status_response["Payload"])
        if "error" in status_data:
            return {
                "error_code": 500,
                "msg": "Log Error",
                "error_type" : "Internal Error",
                "error_reason": "Error while accessing referral status in AddReferral",
                "error_details": payload["error"],
                "request_id": event["request_id"]
            }
        else:
            try:
                payload = {"resource": "Internal Request", "queryStringParameters": {"code": amd_codes["referral_provider_code"]}}
                provider_response = lambda_client.invoke(
                    FunctionName=os.environ["GET_REF_PROVIDER_ARN"],
                    InvocationType="RequestResponse",
                    Payload=json.dumps(payload),
                )
                provider_data = json.load(provider_response["Payload"])
                status_id = status_data["Status Id"]
                provider_id = provider_data["referral_provider_id"] if "referral_provider_id" in provider_data else ""
                current_date = str(datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d'))
                if provider_id:
                    patient_id = event["patient_id"]
                    referral_reason = event["generic_json"]["client"]["referral_type"]
                    if event["generic_json"]["referral_provider"] == "uft":
                        referral_number = "Dependent" if "responsible_party" in event["generic_json"] and event["generic_json"]["responsible_party"] else "Member"
                    else:
                        referral_number = ""
                    referral_ids = []
                    for referral in referral_reason.lower().split("and"):
                        referral_data = {
                            "referralnumber": referral_number,
                            "reason": referral.replace("services", "").strip(),
                            "byreferringproviderid": int(provider_id.replace("rprov", "")),
                            "toreferringproviderid": int(os.environ["TO_PROVIDER_ID"].replace("rprov", "")),
                            "statusid": int(status_id),
                            "referraldiagnosiscodes": [],
                            "referralnotes": [],
                            "excludefromclaim": False,
                            "preauthorizationrequired": False,
                            "patientid": int(event["patient_id"][3:]),
                            "effectivedate": current_date,
                            "expirationdate": None,
                            "authorization": {
                                "authorizationdiagnosiscodes": [],
                                "authorizationnotes": [],
                                "authorizationcounts": [
                                    {
                                        "authorizedunits": 0,
                                        "authorizedamount": 0,
                                        "authorizedminutes": 0,
                                        "authorizedvisits": 0,
                                        "remainingunits": 0,
                                        "remainingamount": 0,
                                        "remainingminutes": 0,
                                        "remainingvisits": 0,
                                        "procedurecodes": [],
                                        "isdefault": True,
                                    }
                                ],
                                "effectivedate": current_date,
                            },
                        }
                        add_referral = requests.post(
                            referral_url,
                            data=json.dumps(referral_data),
                            headers=headers
                        )
                        try:
                            response = json.loads(add_referral.text)
                            referral_ids.append(referral.strip()[0].upper() + str(response["id"]))
                        except KeyError as e:
                            return {
                                "status": 200,
                                "msg" : "Log Error",
                                "error_type" : "KeyError while adding referral",
                                "error_reason": add_referral.reason,
                                "url" : referral_url,
                                "payload" : referral_data,
                                "error_details" : add_referral.text,
                                "request_id": event["request_id"],
                                "patient_id": event["patient_id"],
                                "error": e,
                            }
                        except JSONDecodeError as e:
                            return {
                                "status": 200,
                                "msg" : "Log Error",
                                "error_type" : "JSONDecodeError while adding referral",
                                "error_reason": add_referral.reason,
                                "url" : referral_url,
                                "payload" : referral_data,
                                "error_details" : add_referral.text,
                                "request_id": event["request_id"],
                                "patient_id": event["patient_id"],
                            }
                    return {
                        "status": 200,
                        "msg": "Referral added successfully",
                        "request_id": event["request_id"],
                        "referral_ids": referral_ids,
                        "patient_id": patient_id,
                        "generic_json": event["generic_json"]
                    }
                else:
                    return {
                        "status": 500,
                        "error": "Referral Provider Not Found",
                        "request_id": event["request_id"],
                        "patient_id": event["patient_id"],
                        "generic_json": event["generic_json"]
                    }
            except Exception as e:
                return {
                        "request_id": event.get("request_id", None),
                        "payload": event.get("generic_json", {}),
                        "is_validate": "failed",
                        "error_reason": "Error while adding referral for patient [PATH: /functions/add_referral_for_patient]",
                        "error_exception": str(e)
                    }
