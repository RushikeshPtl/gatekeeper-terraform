import json
import boto3
import requests
import os
import datetime


def lambda_handler(event, context):
    '''
        Function Name : GetReferralStatusID

        - Finds the AMD referral status id of input status

        Parameters:
        -------
        event : dict with input status

        Resonse:
        -------
        dict: having status id
    '''
    if "source" in event and event["source"] == "aws.events":
            print("Warm up triggered..............")
            return {
                "msg" : "Warm up triggered.............."
            }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    pdata = {
        "ppmdmsg": {
            "@action": "selectstatus",
            "@class": "masterfiles",
            "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
            "@ltq": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
            "@la": "getdemographic",
            "@lac": "demographics",
            "@lat": "608",
            "@let": "1664775898421",
            "@lst": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
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
            "msg": "Error while accessing secrets manager",
            "error": payload["error"],
        }
    else:
        token = payload["token"]
        webserver = payload["webserver"]
        cookies = {"token": token}
        resp = requests.post(
            webserver, headers=headers, cookies=cookies, json=pdata
        )
        res = json.loads(resp.text)
        input_status = event.get("input", "")
        status_list = res["PPMDResults"]["record"]
        referral_statuses = []
        for s in status_list:
            if input_status:
                if s["@title"].upper() == input_status.upper():
                    return {
                        "status_code": 200,
                        "msg": "Status Id found.",
                        "Status Id": s["@uid"],
                    }
            else:
                referral_statuses.append({
                    "id" : s["@uid"],
                    "status": s["@title"]
                })
        if referral_statuses:
            response_headers = {
                "Access-Control-Allow-Headers": "*",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS"
            }
            return {
                "statusCode" : 200,
                "headers" : response_headers,
                "body" : json.dumps({
                    "msg" : "Referral Statuses Fetched Successfully",
                    "referral_statuses" : referral_statuses
                })
            }
        else:
            return {
                "status_code": 200,
                "msg": "Status Not Found",
                "response": res
            }
