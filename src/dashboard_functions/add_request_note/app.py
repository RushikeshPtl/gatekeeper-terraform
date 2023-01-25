import json
# from xmlrpc.client import Boolean
from sqlalchemy import create_engine, MetaData, Table, update
import boto3
import os
from sqlalchemy.exc import IntegrityError

response_headers = {
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS"
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
        is_master = payload.get("is_master", False)
        permissions = payload.get("permissions", "")
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

def get_credentials():
    '''
        Invokes the GetSecrets functions to fetch database credentials
    '''
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"secret_type": "Database Credentials"}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        return payload
    else:
        credentials = payload["credentials"]
        return credentials

def lambda_handler(event, context):
    if is_json(event):
        if not isinstance(event, dict):
            event - json.loads(event)
        if "source" in event and event["source"] == "aws.events":
            print("Warm up triggered..............")
            return {
                "msg" : "Warm up triggered.............."
            }
        event = json.loads(event["body"])
        token = event.get("token", "")
        request_id = event.get("request_id", "")
        note = event.get("note", "")

        if request_id and note:
            if token:
                session = authenticate(token=token)
                if "user_id" in session:
                    credentials = get_credentials()
                    if not "error" in credentials:
                        engine = create_engine(
                            "postgresql+psycopg2://{}:{}@{}/{}".format(
                                credentials["username"],
                                credentials["password"],
                                credentials["host"],
                                credentials["db"],
                            )
                        )
                        meta = MetaData(engine)
                        connection = engine.connect()
                        referral_request_notes = Table(
                            "referral_request_notes",
                            meta,
                            autoload = True,
                            autoload_with = engine
                        )
                        add_note = referral_request_notes.insert().values(
                            referral_request_id=request_id,
                            note=note,
                            added_by=session["user_id"]
                        )
                        try:
                            result = connection.execute(add_note)
                        except:
                            return {
                                "statusCode" : 500,
                                "headers" : response_headers,
                                "body" : json.dumps({
                                    "statusCode" : 500,
                                    "msg" : "Something went wrong"
                                }),
                                "isBase64Encoded": False,
                            }
                        return {
                            "statusCode" : 200,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 200,
                                "msg" : "Request Note Added Successfully",
                            }),
                            "isBase64Encoded": False,
                        }
                    else:
                        return {
                            "statusCode" : 500,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 500,
                                "msg": "error while accessing secrets manager",
                                "error": credentials["error"],
                            }),
                            "isBase64Encoded": False,
                        }
                else:
                    return session
            else:
                return {
                    "statusCode": 400,
                    "headers": response_headers,
                    "body":json.dumps({
                        "statusCode": 400,
                        "msg": "Please provide valid token",
                    }),
                    "isBase64Encoded": False,
                }
        else:
            return {
                "statusCode": 400,
                "headers": response_headers,
                "body":json.dumps({
                    "statusCode": 400,
                    "msg": "Please provide request id & note",
                }),
                "isBase64Encoded": False,
            }
    else:
        return {
            "statusCode": 400,
            "headers": response_headers,
            "body": json.dumps({
                "msg": "Failed with issues: Invalid JSON input.",
                "statusCode": 200
            }),
            "isBase64Encoded": False,
        }
