import json
import boto3
import requests
import datetime
import os

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
      Function Name : addPatientDetails

      It will add patient details.

      Parameters :
      event dict : it contains generic json, which have all data for add patient.

      Returns :
      Response : contains patient id, after patient has been added, or return error if any error accured.
   """
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    generic_json = event["generic_json"]
    name = generic_json["client"]["lastname"]\
        + ", "\
        + generic_json["client"]["firstname"]\
        + " "\
        + generic_json["client"]["middle_initial"] if "middle_initial" in generic_json["client"].keys() and generic_json["client"]["middle_initial"]\
        else\
        generic_json["client"]["lastname"] + ", " + generic_json["client"]["firstname"]
    dob = datetime.datetime.strptime(generic_json["client"]["dob"], "%Y-%m-%d").date()
    amd_codes = get_amd_codes(generic_json["referral_provider"])
    fin_class_invoke = lambda_client.invoke(
        FunctionName=os.environ["FIND_FIN_CLASS_ID_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"code" : amd_codes["financial_class"]}),
    )
    fin_class_response = json.load(fin_class_invoke["Payload"])
    fin_class_id = fin_class_response["financial_class"]["id"]
    resp_party = "SELF"
    hipaarelationship = "18"
    
    if "responsible_party_id" in event:
        resp_party = str(event["responsible_party_id"])
    if "relation" in event["generic_json"]["client"]:
        payload = {"input": event["generic_json"]["client"]["relation"]}
        response = lambda_client.invoke(
            FunctionName=os.environ["FIND_RELATIONSHIP_ID_ARN"],
            InvocationType="RequestResponse",
            Payload=json.dumps(payload),
        )
        relationship_response = json.load(response["Payload"])
        hipaarelationship = relationship_response["hipaa_id"]
        std = relationship_response["std"]
    else:
        hipaarelationship = "18"
        std = "1"
    pdata = {
        "ppmdmsg": {
            "@action": "addpatient",
            "@class": "api",
            "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
            "patientlist": {
                "patient": {
                    "@respparty": resp_party,
                    "@name": name,
                    "@sex": generic_json["client"]["gender"][0].upper() if generic_json["client"]["gender"] else "",
                    "@relationship": std,
                    "@hipaarelationship": hipaarelationship,
                    "@dob": str(dob.month) + "/" + str(dob.day) + "/" + str(dob.year),
                    "@chart": "AUTO",
                    "@profile": os.environ["PROFILE_ID"],
                    "@finclass": fin_class_id,
                    "@deceased": "",
                    "@title": None,
                    "@maritalstatus": "6",
                    "@insorder": "",
                    "@employer": "",
                    "address": {
                        "@zip": generic_json["client"]["zip"] if generic_json["client"]["zip"] else "11220",
                        "@city": generic_json["client"]["city"] if generic_json["client"]["city"] else "Brooklyn",
                        "@state": generic_json["client"]["state"] if generic_json["client"]["state"] else "NY",
                        "@countrycode": "USA",
                        "@address1": generic_json["client"]["address1"],
                        "@address2": generic_json["client"]["address2"] if generic_json["client"]["address2"] else "Placeholder",
                    },
                    "contactinfo": {
                        "@homephone": generic_json["client"]["phone"] if "phone" in generic_json["client"].keys() else "",
                        "@officephone": "",
                        "@officeext": "",
                        "@otherphone": generic_json["client"]["mobile_phone"] if "mobile_phone" in generic_json["client"].keys() else "",
                        "@othertype": "C",
                        "@email": generic_json["client"]["email"] if "email" in generic_json["client"].keys() else "",
                    },
                }
            },
            "resppartylist": {"respparty": {"@name": "", "@accttype": ""}},
        }
    }

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
            "error_reason": "Error while accessing secrets manager in AddPatientDetails",
            "request_id": event["request_id"]
        }
    else:
        token = payload["token"]
        webserver = payload["webserver"]
        cookies = {"token": token}
        resp = requests.post(
            webserver, headers=headers, cookies=cookies, json=pdata
        )
        res = json.loads(resp.text)
        try:
            if res["PPMDResults"]["Results"]["@success"] == "1":
                patient_id = res["PPMDResults"]["Results"]["patientlist"]["patient"]["@id"]
                return {
                    "status_code": 200,
                    "msg": "Add Patient Note",
                    "patient_id": patient_id,
                    "request_id": event["request_id"],
                    "generic_json": generic_json,
                }
            elif res["PPMDResults"]["Results"]["@success"] == "0":
                return {
                    "status_code": 200,
                    "msg": "Error while adding patient",
                    "request_id": event["request_id"],
                    "error_json": res["PPMDResults"],
                    "url": webserver,
                    "payload": pdata
                }
        except:
            return {
                "status_code": 500,
                "msg": "Log Error",
                "error_type" : "Error while adding patient",
                "error_details": res,
                "error_reason": resp.reason,
                "request_id": event["request_id"],
                "url": webserver,
                "payload": pdata
            }
