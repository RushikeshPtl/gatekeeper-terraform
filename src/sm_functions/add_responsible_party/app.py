import requests
import boto3
import datetime
import json
import os


def convertDate(cdate):
    format = "%Y-%m-%d"
    codate = datetime.datetime.strptime(cdate, format).date()
    converted_date = datetime.date.strftime(codate, "%m/%d/%Y")
    return converted_date

def lambda_handler(event, context):
    client = boto3.client("lambda")
    payload = {"input": event["generic_json"]["client"]["relation"]}
    response = client.invoke(
        FunctionName=os.environ["FIND_RELATIONSHIP_ID_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps(payload),
    )
    try:
        relationship_response = json.load(response["Payload"])
        hipaarelationship = relationship_response["hipaa_id"]
        std = relationship_response["std"]
        responsible_party = event["generic_json"]["responsible_party"]
        middleinitial = " " + responsible_party["middle_initial"] if responsible_party["middle_initial"] else ""
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        pdata3 = {
            "ppmdmsg": {
                "@action": "addrespparty",
                "@class": "demographics",
                "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
                "@ltq": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
                "@patientid": event.get("patient_id", ""),
                "@hipaarelationship": hipaarelationship,
                "@relationship": std,
                "@la": "lookuprespparty",
                "@lac": "lookup",
                "@lat": "484",
                "@let": "1589908200838",
                "@lst": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
                "respparty": {
                    "@name": event["generic_json"]["responsible_party"]["lastname"]
                    + ","
                    + event["generic_json"]["responsible_party"]["firstname"]
                    + middleinitial,
                    "@dob": convertDate(responsible_party["dob"]) if "dob" in responsible_party and responsible_party["dob"] else "",
                    "@sex": {
                        event["generic_json"]["responsible_party"]["gender"]
                        == "female": "F",
                        event["generic_json"]["responsible_party"]["gender"] == "male": "M",
                    }.get(True, "U"),
                    "@employer": "",
                    "@employstatus": "",
                    "@acctype": "4",
                    "@billcycle": "",
                    "@title": None,
                    "@sendstmt": "",
                    "@stmtrestart": "",
                    "@ispaperless": "",
                    "@stmtformat": "",
                    "@billcycle": "",
                    "@fincharge": "",
                    "address": {
                        "@zip": event["generic_json"]["responsible_party"]["zip"] if event["generic_json"]["responsible_party"]["zip"] else "11220",
                        "@city": event["generic_json"]["responsible_party"]["city"] if event["generic_json"]["responsible_party"]["city"] else "Brooklyn",
                        "@state": event["generic_json"]["responsible_party"]["state"] if event["generic_json"]["responsible_party"]["state"] else "NY",
                        "@countrycode": "USA",
                        "@address1": event["generic_json"]["responsible_party"]["address1"],
                        "@address2": event["generic_json"]["responsible_party"]["address2"] if event["generic_json"]["responsible_party"]["address2"] else "Placeholder",
                    },
                    "contactinfo": {
                        "@homephone": event["generic_json"]["responsible_party"]["phone"],
                        "@officephone": "",
                        "@officeext": "",
                        "@otherphone": event["generic_json"]["responsible_party"][
                            "mobile_phone"
                        ],
                        "@othertype": "",
                        "@preferredcommunicationfid": "",
                        "@communicationnote": "",
                        "@email": event["generic_json"]["responsible_party"]["email"],
                    },
                },
                "familychanges": {},
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
                "error_reason": "Error while accessing secrets manager in AddResponsibleParty",
                "request_id": event["request_id"]
            }
        else:
            token = payload["token"]
            webserver = payload["webserver"]
            cookies = {"token": token}
            resp = requests.post(
                webserver, headers=headers, cookies=cookies, json=pdata3
            )
            res = json.loads(resp.text)
            try:
                if res["PPMDResults"]["Results"]["@success"] == "1":
                    msg =  "Add Patient" if event["msg"] == "Add patient & responsible party" else "Add Patient Note"
                    responsible_party_id = res["PPMDResults"]["Results"]["respparty"]["@id"]
                    return {
                        "status_code": 200,
                        "msg": msg,
                        "patient_id": event["patient_id"],
                        "responsible_party_id": responsible_party_id,
                        "generic_json": event["generic_json"],
                        "request_id": event["request_id"],
                        "account_type": res["PPMDResults"]["Results"]["respparty"]["@accttype"],
                    }
                elif res["PPMDResults"]["Results"]["@success"] == "0":
                    return {
                        "status_code": 200,
                        "msg": "Error while adding responsible party",
                        "request_id": event["request_id"],
                        "error_json": res["PPMDResults"],
                        "url": webserver,
                        "payload": pdata3
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
                    "payload": pdata3
                }
    except Exception as e:
        return {
                "request_id": event.get("request_id", None),
                "payload": event.get("generic_json", {}),
                "is_validate": "failed",
                "error_reason": "Something went wrong in add responsible party [PATH: /functions/add_responsible_party]",
                "error_exception": str(e)
            }
