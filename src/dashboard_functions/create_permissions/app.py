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
        if is_master or ("Allowed" in permissions and "create_permissions" in permissions["Allowed"]):
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
            event = json.loads(event)
        if "source" in event and event["source"] == "aws.events":
            print("Warm up triggered..............")
            return {
                "msg" : "Warm up triggered.............."
            }
        event = json.loads(event["body"])
        token = event.get("token", "")
        if token:
            session = authenticate(token=token)
            if "user_id" in session:
                user_id = session["user_id"]
                category = event.get("category", None)
                level = event.get("level", None)
                display_name = event.get("display_name", None)
                description = event.get("description", None)

                if category and level and display_name:
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
                        permissions = Table(
                            "permissions",
                            meta,
                            autoload = True,
                            autoload_with = engine
                        )
                        insert_permissions = permissions.insert().values(
                            category = category,
                            level = level,
                            display_name = display_name.strip(),
                            description = description
                        )
                        try:
                            result = connection.execute(insert_permissions)
                            permission_id = result.inserted_primary_key[0]
                            statusCode = 200
                            response = {
                                "statusCode" : 200,
                                "msg" : "Permission created successfully",
                                "permission_id" : permission_id
                            }
                        except IntegrityError as ig:
                            statusCode = 400
                            response = {
                                "statusCode" : 400,
                                "msg" : ig.args[0].split("DETAIL:  ")[1].strip()
                            }
                        return {
                            "statusCode" : statusCode,
                            "headers" : response_headers,
                            "body" : json.dumps(response),
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
                    return {
                        "statusCode": 400,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 400,
                            "msg": "All fields are mendatory",
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
        response = {
            "statusCode": 400,
            "headers": response_headers,
            "body": json.dumps({
                "msg": "Failed with issues: Invalid JSON input.",
                "statusCode": 200
            }),
            "isBase64Encoded": False,
        }
        return response
            
