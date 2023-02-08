from datetime import datetime
import json
from random import randint
from uuid import uuid4
import boto3
import json
import os

response_headers = {
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, PUT, OPTIONS"
    }
lambda_client = boto3.client("lambda")

def is_json(json_data):
    try:
        if not isinstance(json_data, dict):
            json.loads(json_data)
        else:
            return True
    except ValueError:
        return False
    return True

def authenticate(token):
    '''
        Invokes the GetSessionUser to verify the session token & fetch user_id

        Input:
            - token(REQUIRED) : String
        Output:
            - dict
    '''
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_USER_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"type": "session_token", "token": token}),
    )
    payload = json.load(response["Payload"])
    error = None
    statusCode, error =  (400, "error while accessing token") if "error" in payload else (400, payload["msg"]) if "user_id" not in payload else (200, None)
    if error:
        return {
                "statusCode": statusCode,
                "headers": response_headers,
                "body" : json.dumps({
                    "statusCode": statusCode,
                    "msg": error
                }),
                "isBase64Encoded": False,
            }
    else:
        permissions = payload.get("permissions", "")
        is_master = payload.get("is_master", False)
        if is_master or (permissions and "Allowed" in permissions and "edit_referral_request" in permissions["Allowed"]):
            return {
                "user_id" : payload["user_id"],
            }
        else:
            return {
                "statusCode": 400,
                "headers": response_headers,
                "body":json.dumps({
                    "statusCode": 400,
                    "msg": "Unauthorized user",
                }),
                "isBase64Encoded": False,
            }


def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    resource = event.get("resource", "")
    client = boto3.client("stepfunctions")
    referral_from = "uft" if resource == "/api/member" else event["pathParameters"]["type"]
    environment = os.environ["ENVIRONMENT"]
    account_id = os.environ["ACCOUNT_ID"]
    request_id = event["pathParameters"]["request_id"] if "pathParameters" in event and event["pathParameters"] and "request_id" in event["pathParameters"] else None
    token = event["queryStringParameters"].get("token", None) if "queryStringParameters" in event and event["queryStringParameters"] else None
    if request_id:
        if token:
            session = authenticate(token)
            if "user_id" not in session:
                return session
        else:
            return {
                "statusCode": 400,
                "headers": response_headers,
                "body":json.dumps({
                    "statusCode": 400,
                    "msg": "Please send valid token...",
                }),
                "isBase64Encoded": False,
            }
    if (is_json(event)):
        if not isinstance(event, dict):
            event = json.loads(event)
        data = json.loads(event["body"])
        data["referral_provider"] = referral_from.lower()
        data["request_id"] = request_id
        
        if not referral_from:
            return {
                "statusCode": 400,
                "headers": response_headers,
                "body": json.dumps({
                    "msg": "Failed with issues: Please provide valid referral provider",
                    "code": 200
                }
                ),
                "isBase64Encoded": False,
            }
        else:
            # stepmachine_arn
            response = client.start_sync_execution(
                stateMachineArn="arn:aws:states:us-east-1:{}:stateMachine:{}AddUFTReferralToEMR".format(account_id, environment),
                name="AddUFTReferralToEMR",
                input=json.dumps(data)
            )
            return {
                "statusCode": 200,
                "headers": response_headers,
                "body": response["output"],
                "isBase64Encoded": False,
            }
    else:
        response = {
            "statusCode": 400,
            "headers": response_headers,
            "body": json.dumps({
                "msg": "Failed with issues: Invalid JSON input.",
                "code": 200
            }),
            "isBase64Encoded": False,
        }
        return response