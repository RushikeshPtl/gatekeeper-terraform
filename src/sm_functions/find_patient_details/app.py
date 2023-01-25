import json
import boto3
import requests
import datetime
import os



def compare_responsible_party(patient_id, generic_resp_party, url, headers, cookies):
    demographic = {
        "ppmdmsg": {
            "@action": "getdemographic",
            "@class": "api",
            "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
            "@patientid": patient_id,
        }
    }
    demographic_data = requests.post(
        url, headers=headers, cookies=cookies, json=demographic
    )
    responsible_parties = json.loads(demographic_data.text)["PPMDResults"]["Results"][
        "resppartylist"
    ]
    responsible_parties = (
        [responsible_parties]
        if type(responsible_parties) != list
        else responsible_parties
    )
    dob = datetime.datetime.strptime(generic_resp_party["dob"], "%Y-%m-%d").date() if "dob" in generic_resp_party and generic_resp_party["dob"] else None
    middleinitial = " " + generic_resp_party["middle_initial"] if generic_resp_party["middle_initial"] else ""
    generic_name, generic_dob = (
        generic_resp_party["lastname"] + "," + generic_resp_party["firstname"] + middleinitial,
        dob
    )
    resp_party_id = None
    for party in responsible_parties:
        resp_party = party["respparty"]
        resp_name, resp_dob = (
            resp_party["@name"],
            datetime.datetime.strptime(resp_party["@dob"], "%m/%d/%Y").date() if "@dob" in resp_party and resp_party["@dob"] else ""
        )
        if (
            resp_name == generic_name.upper()
            and generic_dob and resp_dob == generic_dob
        ):
            resp_party_id = resp_party["@id"]
    return resp_party_id


def Patients(patientList, gcName, gcDob):
    for p in patientList:
        format = "%m/%d/%Y"
        dob = datetime.datetime.strptime(p["@dob"], format).date()
        patient_name = p["@name"]
        if patient_name == gcName.upper() and dob == gcDob:
            pId = p["@id"]
            return pId
    return None

def lookup_patient(webserver, cookies, headers, event, page):
    lastname = event["generic_json"]["client"]["lastname"]
    firstname = event["generic_json"]["client"]["firstname"]
    middlename = " " + event["generic_json"]["client"]["middle_initial"] if event["generic_json"]["client"]["middle_initial"] else ""
    pdata = {
        "ppmdmsg": {
            "@action": "lookuppatient",
            "@class": "api",
            "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
            "@exactmatch": "-1",
            "@name": lastname
            + ","
            + firstname
            + middlename,
            "@page": page,
            "@nocookie": "0",
        }
    }
    resp = requests.post(webserver, headers=headers, cookies=cookies, json=pdata)
    res = json.loads(resp.text)
    try:
        if res["PPMDResults"]["Error"]:
            return {
                "status_code": "200",
                "msg": "Error while looking for patient",
                "error_json": res["PPMDResults"]["Error"],
                "request_id": event["request_id"],
                "generic_json": event["generic_json"],
                "url" : webserver,
                "payload" : pdata
            }
        else:
            return res["PPMDResults"]["Results"]["patientlist"]
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


def lambda_handler(event, context):

    headers = {"Content-Type": "application/json",  "Accept":  "application/json"}

    pdata = {
        "ppmdmsg": {
            "@action": "lookuppatient",
            "@class": "api",
            "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
            "@exactmatch": "-1",
            "@name": event["generic_json"]["client"]["lastname"]
            + ","
            + event["generic_json"]["client"]["firstname"],
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
            "error_reason": "Error while accessing secrets manager in FindPatientDetails",
            "request_id": event["request_id"]
        }
    else:
        token = payload["token"]
        webserver = payload["webserver"]
        cookies = {"token": token}
        resp = requests.post(webserver, headers=headers, cookies=cookies, json=pdata)

        res = json.loads(resp.text)

        generic_json_p = event["generic_json"]
        gclient = generic_json_p["client"]
        middlename = " " + event["generic_json"]["client"]["middle_initial"] if event["generic_json"]["client"]["middle_initial"] else ""
        gcName = gclient["lastname"] + "," + gclient["firstname"] + middlename
        gcDob = datetime.datetime.strptime(gclient["dob"], "%Y-%m-%d").date()
        msg = " & responsible party" if "responsible_party" in generic_json_p and generic_json_p["responsible_party"] else ""
        lookup_patients = lookup_patient(webserver, cookies, headers, event, 1)
        if not "msg" in lookup_patients:
            item_count = int(lookup_patients["@itemcount"])
            if item_count > 0:
                patientList = lookup_patients["patient"] if item_count > 1 else [lookup_patients["patient"]]
                pages = int(lookup_patients["@pagecount"])
                if pages > 1:
                    for page in range(2, pages):
                        patients = lookup_patient(webserver, cookies, headers, event, page)
                        if not "msg" in patients:
                            patients = [patients["patient"]] if not isinstance(patients["patient"], list) else patients["patient"]
                            patientList.extend(patients)
                        else:
                            return patients
                patient_id = Patients(patientList, gcName, gcDob)
                if patient_id:
                    if "responsible_party" in generic_json_p and generic_json_p["responsible_party"]:
                        resp_id = compare_responsible_party(
                            patient_id,
                            generic_json_p["responsible_party"],
                            webserver,
                            headers,
                            cookies,
                        )
                        if resp_id:
                            return {
                                "status_code": 200,
                                "msg": "Patient & Responsible already registered",
                                "patient_id": patient_id,
                                "request_id": event["request_id"],
                                "responsible_party_id": resp_id,
                                "generic_json": generic_json_p
                            }
                        else:
                            return {
                                "status_code": 200,
                                "msg": "Add responsible party",
                                "patient_id": patient_id,
                                "request_id": event["request_id"],
                                "generic_json": generic_json_p,
                            }
                    else:
                        return {
                            "status_code": 200,
                            "msg": "Patient exists & Responsible party not present in generic",
                            "generic_json": generic_json_p,
                            "request_id": event["request_id"],
                            "patient_id": patient_id
                        }
                else:
                    return {
                        "status_code": 200,
                        "msg": "Add patient" + msg,
                        "request_id": event["request_id"],
                        "generic_json": generic_json_p,
                    }
            else:
                return {
                    "status_code": 200,
                    "msg": "Add patient" + msg,
                    "request_id": event["request_id"],
                    "generic_json": generic_json_p,
                }
        else:
            return lookup_patients
