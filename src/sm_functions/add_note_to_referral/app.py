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
    if "referral_ids" in event:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        note = getNote(event)
        if note:
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
                    "error_reason": "Error while accessing secrets manager in AddNoteToReferral",
                    "request_id": event["request_id"]
                }
            else:
                token = payload["token"]
                headers["Authorization"] = "Bearer {}".format(token)
                webserver = payload["webserver"]
                referral_note_url = webserver.replace("xmlrpc/processrequest.aspx","").replace("processrequest", "api") + "referral/Notes"
                for referral_id in event["referral_ids"]:
                    data = {
                        "referralid": int(referral_id[1:]),
                        "notetext": note
                    }
                    response = requests.post(
                        referral_note_url,
                        data=json.dumps(data),
                        headers=headers
                    )
                    try:
                        response_data = json.loads(response.text)
                    except:
                        return {
                        "status": 500,
                        "msg": "Error while adding referral note",
                        "error": "Error while adding referral note",
                        "request_id": event["request_id"],
                        "patient_id": event["patient_id"],
                        "url": referral_note_url,
                        "payload": data
                        }
                return {
                    "status": 200,
                    "msg": "Referral notes added successfully",
                    "request_id": event["request_id"],
                    "referral_ids": event["referral_ids"],
                    "patient_id": event["patient_id"],
                }
        else:
            return {
                    "status": 200,
                    "msg": "Referral added successfully",
                    "request_id": event["request_id"],
                    "referral_ids": event["referral_ids"],
                    "patient_id": event["patient_id"],
                }
    else:
        return {
            "status": 200,
            "msg": "Process completed without adding referral",
            "request_id": event["request_id"],
            "referral_ids": event["referral_ids"],
            "patient_id": event["patient_id"],
        }




