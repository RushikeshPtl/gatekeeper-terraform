import json
import boto3
from datetime import datetime, timedelta
import os

response_headers = {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                }
lambda_client = boto3.client("lambda")

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
        role_level = 0 if is_master else payload["role_level"] if "role_level" in payload and payload["role_level"] else 10
        if permissions:
            return {
                "user_id" : payload["user_id"],
                "permissions" : permissions
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
    token = event["queryStringParameters"].get("token","") if "queryStringParameters" in event and event["queryStringParameters"] != None else ""
    if token:
        session = authenticate(token)
        if "user_id" in session:
            return {
                "statusCode" : 200,
                "headers" : response_headers,
                "body" : json.dumps({
                    "statusCode" : 200,
                    "msg" : "Permissions JSON Fetched Successfully",
                    "permissions" : session["permissions"]
                }),
                "isBase64Encoded": False,
            }
        else:
            return session
    else:
        return {
            "statusCode" : 400,
            "headers" : response_headers,
            "body" : json.dumps({
                "statusCode" : 400,
                "msg" : "PPlease send valid token",
            }),
            "isBase64Encoded": False,
        }