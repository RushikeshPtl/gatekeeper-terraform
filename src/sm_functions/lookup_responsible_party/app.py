import json
import boto3
import requests
import datetime
import os


def RespParties(RespList, grName, grDob):
    for r in RespList:
        format = "%m/%d/%Y"
        dob = datetime.datetime.strptime(r["@dob"], format).date() if "@dob" in r and r["@dob"] else ""
        pCompareSsn = r["@ssn"][-4:]
        if (
            r["@name"] == grName.upper()
            and str(dob) == grDob
        ):
            rId = r["@id"]
            return rId
    return None


def lambda_handler(event, context):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    responsible_party = event["generic_json"]["responsible_party"]\
                    if "responsible_party" in event["generic_json"] and event["generic_json"]["responsible_party"]\
                    else event["generic_json"]["client"]
    middlename = " " + responsible_party["middle_initial"] if responsible_party["middle_initial"] else ""
    pdata = {
        "ppmdmsg": {
            "@action": "lookuprespparty",
            "@class": "api",
            "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
            "@exactmatch": "-1",
            "@name": responsible_party["lastname"]
            + ","
            + responsible_party["firstname"]
            + middlename,  # last_name,first_name
            "@page": "1",
            "@nocookie": "0",
        }
    }

    client = boto3.client("lambda")
    response = client.invoke(
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
            "error_reason": "Error while accessing secrets manager in LookupResponsibleParty",
            "request_id": event["request_id"]
        }
    else:
        try:
            token = payload["token"]
            webserver = payload["webserver"]
            cookies = {"token": token}
            resp = requests.post(
                webserver, headers=headers, cookies=cookies, json=pdata
            )
            res = json.loads(resp.text)
            generic_json_p = event["generic_json"]
            lastname = responsible_party["lastname"] + "," if responsible_party["lastname"] else ""
            firstname = responsible_party["firstname"] if responsible_party["firstname"] else ""
            middleinitial = " " + responsible_party["middle_initial"] if responsible_party["middle_initial"] else ""
            grName = lastname + firstname + middleinitial
            grDob = responsible_party["dob"]
            try:
                if res["PPMDResults"]["Error"] is not None:
                    return {
                        "status_code": "200",
                        "msg": "Error while looking for responsible party",
                        "error_json": res["PPMDResults"]["Error"],
                        "request_id": event["request_id"],
                        "generic_json": generic_json_p,
                        "url" : webserver,
                        "payload" : pdata
                    }
                elif int(res["PPMDResults"]["Results"]["resppartylist"]["@itemcount"]) >= 1:
                    respPartyList = res["PPMDResults"]["Results"]["resppartylist"]["respparty"]
                    respPartyItemcount = res["PPMDResults"]["Results"]["resppartylist"][
                        "@itemcount"
                    ]
                    RespList = (
                        [respPartyList] if int(respPartyItemcount) == 1 else respPartyList
                    )
                    respParty_id = RespParties(RespList, grName, grDob)
                    if respParty_id:
                        msg = "Add patient" if "patient_id" not in event.keys() else "Add patient note"
                        patient_id = None if "patient_id" not in event.keys() else event["patient_id"]
                        return {
                            "status_code": 200,
                            "msg": msg,
                            "responsible_party_id": respParty_id,
                            "request_id": event["request_id"],
                            "generic_json": generic_json_p,
                            "patient_id": patient_id
                        }
                    else:
                        msg = event["msg"]
                        patient_id = event["patient_id"] if "patient_id" in event.keys() else None
                        return {
                            "status_code": 200,
                            "msg": msg,
                            "request_id": event["request_id"],
                            "generic_json": generic_json_p,
                            "patient_id": patient_id
                        }
                else:
                    msg = event["msg"]
                    patient_id = event["patient_id"] if "patient_id" in event.keys() else None
                    return {
                        "status_code": 200,
                        "msg": msg,
                        "request_id": event["request_id"],
                        "generic_json": generic_json_p,
                        "patient_id": patient_id
                    }
            except:
                return {
                    "error_code": 500,
                    "msg": "Log Error",
                    "error_type" : "Error while calling AMD API",
                    "error_details": res,
                    "error_reason": resp.reason,
                    "request_id": event["request_id"],
                    "url": webserver,
                    "payload": pdata
                }
        except Exception as e:
            return {
                    "request_id": event.get("request_id", None),
                    "payload": event.get("generic_json", {}),
                    "is_validate": "failed",
                    "error_reason": "Something went wrong in lookup responsible party [PATH: /functions/lookup_responsible_party]",
                    "error_exception": str(e),
                    "msg": "Log Error",
                }
