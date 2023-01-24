import json
import boto3
import requests
import os
import datetime

def get_api_data():
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
        return payload

def lambda_handler(event, context):
    '''
        Function Name : LookUpFinancialClass

        - Lookes for the AMD Financial Class

        Parameters:
        -------
        event : dict with financial class name

        Resonse:
        -------
        dict: having id, code & name of matching financial classes
    '''
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    code = event.get("code", "")
    payload = {
                "ppmdmsg": {
                    "@action": "lookupfinclass",
                    "@class": "api",
                    "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
                    "@exactmatch": "0",
                    "@orderby":"name",
                    "@name": "",
                    "@page": "1",
                    "@code": code,
                    "@nocookie": "0"
                }
            }
    api_data = get_api_data()
    if not "error" in api_data:
        webserver = api_data["webserver"]
        cookies = {"token": api_data["token"]}
        response = requests.post(
            webserver, headers=headers, cookies=cookies, json=payload
        )
        response = json.loads(response.text)
        if not response["PPMDResults"]["Error"]:
            classes = response["PPMDResults"]["Results"]["finclasslist"]["finclass"]
            financial_classes = []
            if code:
                if classes["@code"] == code:
                    cls = {}
                    cls["id"] = classes["@id"]
                    cls["code"] = classes["@code"]
                    cls["name"] = classes["@name"]
                    return {
                        "statusCode" : 200,
                        "msg" : "Financial class fetched successfully",
                        "financial_class" : cls
                    }
            for f in classes:
                financial_classes.append({
                    "id" : f["@id"],
                    "code": f["@code"],
                    "name": f["@name"]
                })

            if financial_classes:
                response_headers = {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, OPTIONS"
                }
                return {
                    "statusCode" : 200,
                    "headers" : response_headers,
                    "body" : json.dumps({
                        "msg" : "Financial classes Fetched Successfully",
                        "financial_class" : financial_classes
                    })
                }
            else:
                return {
                    "status_code": 200,
                    "msg": "Class Not Found",
                    "response": response
                }
        else:
            return {
                "status_code": 200,
                "msg": "Class Not Found",
                "response": response
            }  
    else:
        return {
            "error_code": 500,
            "msg": "Error while accessing secrets manager",
            "error": payload["error"],
        }
