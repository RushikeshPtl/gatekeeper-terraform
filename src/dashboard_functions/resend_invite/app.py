import json
# from xmlrpc.client import Boolean
from sqlalchemy import create_engine, MetaData, Table, select
import boto3
import os
import uuid

response_headers = {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, PUT",
                }
lambda_client = boto3.client("lambda")

class ApiError(Exception):
    def __init__(self, code, message="Api Error"):
        self.code = code
        self.message = message
        super().__init__(self.message)

def get_token(event):
    if "queryStringParameters" in event and event["queryStringParameters"] and "token" in event["queryStringParameters"]:
        return event["queryStringParameters"]["token"]
    else:
        raise ApiError(400, "Please provide token")

def get_user_id(event):
    if "pathParameters" in event and event["pathParameters"] and "id" in event["pathParameters"]:
        return event["pathParameters"]["id"]
    else:
        raise ApiError(400, "Please provide user id")

def authorize(token):
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_USER_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"type": "session_token", "token": token}),
    )
    payload = json.load(response["Payload"])
    allowed_permissions = payload.get("permissions", {}).get("Allowed", [])
    is_master = payload.get("is_master", False)
    permission = f"add_user"
    if 'error' in payload:
        raise ApiError(500, 'Error while accessing token')

    if 'user_id' not in payload:
        raise ApiError(500, str(payload["msg"]))

    if not is_master and permission not in allowed_permissions:
        raise ApiError(401, 'Unauthorized user')

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
    if 'error' in payload:
        raise ApiError(
            500, f"accessing secrets manager got an error: {str(payload['error'])}")

    return payload['credentials']

def create_db_engine_and_meta(db_credentials):
    engine = create_engine(
        "postgresql+psycopg2://{}:{}@{}/{}".format(
            db_credentials["username"],
            db_credentials["password"],
            db_credentials["host"],
            db_credentials["db"]
        )
    )
    meta = MetaData(engine)

    return engine, meta

def get_user_data(user_id, engine, meta):
    users = Table(
        "users",
        meta,
        autoload=True,
        autoload_with=engine
    )
    stmt = select([
        users.columns.id,
        users.columns.first_name,
        users.columns.last_name,
        users.columns.email,
        users.columns.is_verified
    ]).where(
        users.columns.id == int(user_id),
        users.columns.archived == False
    )
    connection = engine.connect()
    results = connection.execute(stmt).fetchone()
    if results:
        if results["is_verified"] == False:
            return results["first_name"] + " " + results["last_name"], results["email"]
        else:
            raise ApiError(400, "User is already verified use forgot password instead")
    else:
        raise ApiError(400, "User not found")


def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    try:
        token = get_token(event)
        authorize(token)
        user_id = get_user_id(event)
        db_credentials = get_credentials()
        engine, meta = create_db_engine_and_meta(db_credentials)
        name, email = get_user_data(user_id, engine, meta)
        set_credentials_token = uuid.uuid4().hex.upper()
        send_email = lambda_client.invoke(
                FunctionName=os.environ["SEND_EMAIL_ARN"],
                InvocationType="Event",
                Payload=json.dumps({
                    "type": "Invite",
                    "email": email,
                    "name": name,
                    "first_login_token": set_credentials_token
                    }
                ),
            )
        save_token = lambda_client.invoke(
                FunctionName=os.environ["UPDATE_S3_ARN"],
                InvocationType="Event",
                Payload=json.dumps({
                    "token_type": "first_login_token",
                    "s3_type": "add",
                    "token" : set_credentials_token,
                    "user_id" : user_id
                    }
                ),
            )
        return {
            "statusCode" : 200,
            "headers" : response_headers,
            "body" : json.dumps({
                "msg" : "Invite Sent"
            })
        }
    except ApiError as e:
        return {
            "statusCode": e.code,
            "headers": response_headers,
            "body": json.dumps({
                "statusCode": e.code,
                "msg": e.message,
            })
        }
        