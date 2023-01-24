import json
import boto3
import requests
import os
import datetime


def getNote(event):
    note = ""
    referring_provider = event["generic_json"]["referring_provider"]
    if referring_provider:
        refprovider_name = referring_provider.get("name", "")
        refprovider_email = referring_provider.get("email", "")
        refprovider_phone = referring_provider.get("phone", "")
        client_note = event["generic_json"]["client"].get("note", "")
        if event["generic_json"]["referral_provider"] == "uft":
            note = "Referring Provider :\n"
            note = note + f"Name : {refprovider_name} \n" if refprovider_name else note
            note = note + f"Email : {refprovider_email} \n" if refprovider_email else note
            note = note + f"Phone : {refprovider_phone} \n" if refprovider_phone else note
            note = note + f"Comment : {client_note}" if client_note else note
            return note
        else:
            note = "Comment : {}".format(client_note)
            return note
    else:
        return None


def lambda_handler(event, context):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    note = getNote(event)
    if note:
        pdata3 = {
            "ppmdmsg": {
                "@action": "savepatientnotes",
                "@class": "api",
                "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
                "@id": event["patient_id"][3:],
                "@useclienttime": "1",
                "masterfile": {
                    "@uid": "",
                    "@patientfid": event["patient_id"][3:],
                    "@profilefid": "2871",
                    "@notetypefid": "10",
                    "@note": note,
                },
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
            "error_reason": "Error while accessing secrets manager in AddNoteToPatient",
            "request_id": event["request_id"]
        }
        else:
            token = payload["token"]
            webserver = payload["webserver"]
            cookies = {"token": token}
            resp = requests.post(
                webserver,
                headers=headers,
                cookies=cookies,
                json=pdata3,
            )
            res = json.loads(resp.text)
            try:
                if "Error" not in res["PPMDResults"] and "record" in res["PPMDResults"]:
                    return {
                        "status_code": 200,
                        "msg": "Note added",
                        "request_id": event["request_id"],
                        "patient_id": event["patient_id"],
                        "generic_json": event["generic_json"]
                    }
                else:
                    return {
                        "status_code": 200,
                        "msg": "Error while adding note",
                        "error_json": res["PPMDResults"],
                        "request_id": event["request_id"],
                        "patient_id": event["patient_id"],
                        "generic_json": event["generic_json"],
                        "url": webserver,
                        "payload": pdata3
                    }
            except:
                return {
                        "status_code": 200,
                        "msg": "Log Error",
                        "error_type" : "Error while calling AMD API",
                        "error_details": res,
                        "error_reason": "Error while adding patient note",
                        "request_id": event["request_id"],
                        "payload": pdata3,
                        "url": webserver
                    }
    else:
        return {
            "status_code": 200,
            "msg": "No referring provider",
            "request_id": event["request_id"],
            "patient_id": event["patient_id"],
            "generic_json": event["generic_json"]
        }
