import json
# from xmlrpc.client import Boolean
from sqlalchemy import create_engine, MetaData, Table, update, select
import boto3
import os
from datetime import datetime
import re
from sqlalchemy.exc import IntegrityError
import uuid

response_headers = {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST, PUT",
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
        role_level = 0 if is_master else payload["role_level"] if "role_level" in payload and payload["role_level"] else 10
        if is_master or (permissions and "Allowed" in permissions and "add_user" in permissions["Allowed"]):
            return {
                "user_id" : payload["user_id"],
                "is_master" : is_master,
                "role_level" : role_level
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
            session = authenticate(token)
            if "user_id" in session:
                first_name = event["first_name"]
                last_name = event["last_name"]
                email = event["email"]
                role = event["role_id"]
                phone = event.get("phone", None)
                issues = []

                pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                if not re.match(pattern, email):
                    issues.append("Invalid email field")

                if phone and not all(str.isdigit(char) or char in ["-", "(", ")"] for char in phone):
                    issues.append("Invalid phone field")

                if issues:
                    response = {
                        "statusCode" : 400,
                        "msg" : "Invalid request",
                        "issues" : issues
                    }
                    return {
                        "statusCode" : 400,
                        "headers": response_headers,
                        "body": json.dumps(response),
                        "isBase64Encoded": False,
                    }
                else:
                    response = lambda_client.invoke(
                        FunctionName=os.environ["GET_SECRET_ARN"],
                        InvocationType="RequestResponse",
                        Payload=json.dumps({"secret_type": "Database Credentials"}),
                    )
                    payload = json.load(response["Payload"])
                    if "error" in payload:
                        return {
                            "statusCode" : 500,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 500,
                                "msg": "error while accessing secrets manager",
                                "error": payload["error"],
                            }),
                            "isBase64Encoded": False,
                        }
                    else:
                        credentials = payload["credentials"]
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
                        users = Table(
                            "users",
                            meta,
                            autoload=True,
                            autoload_with=engine
                        )
                        roles = Table(
                            "roles",
                            meta,
                            autoload = True,
                            autoload_with = engine
                        )

                        select_roles = select([
                            roles.columns.id
                        ]).where(
                            roles.columns.role_level > session["role_level"]
                        )
                        try:
                            allowed_roles = [role["id"] for role in connection.execute(select_roles).fetchall()]
                        except:
                            return {
                                "statusCode" : 500,
                                "headers" : response_headers,
                                "body" : json.dump({
                                    "statusCode" : 500,
                                    "msg" : "Something went wrong"
                                }),
                                "isBase64Encoded": False,
                            }
                        if session["is_master"] or (allowed_roles and int(role) in allowed_roles):
                            insert_user = users.insert().values(
                                first_name = first_name,
                                last_name = last_name,
                                email = email,
                                role_id = int(role),
                                phone = phone
                            )
                            user_id = None
                            try:
                                result = connection.execute(insert_user)
                                user_id = result.inserted_primary_key[0]
                                statusCode = 200
                                response = {
                                    "statusCode" : 200,
                                    "msg" : "User registered successfully",
                                    "user_id" : user_id
                                }

                            except IntegrityError as ig:
                                statusCode = 400
                                response = {
                                    "statusCode" : 400,
                                    "msg" : ig.args[0].split("DETAIL:  ")[1].strip()
                                }
                            if user_id:
                                first_login_token = uuid.uuid4().hex.upper()
                                send_email = lambda_client.invoke(
                                        FunctionName=os.environ["SEND_EMAIL_ARN"],
                                        InvocationType="Event",
                                        Payload=json.dumps({
                                            "type": "Invite",
                                            "email": email,
                                            "name": first_name + " " + last_name,
                                            "first_login_token": first_login_token
                                            }
                                        ),
                                    )
                                save_token = lambda_client.invoke(
                                        FunctionName=os.environ["UPDATE_S3_ARN"],
                                        InvocationType="Event",
                                        Payload=json.dumps({
                                            "token_type": "first_login_token",
                                            "s3_type": "add",
                                            "token" : first_login_token,
                                            "user_id" : user_id
                                            }
                                        ),
                                    )
                                add_permissions = lambda_client.invoke(
                                    FunctionName=os.environ["UPDATE_USER_PERMISSION_ARN"],
                                    InvocationType="Event",
                                    Payload=json.dumps({
                                        "resource" : "Internal Request",
                                        "user_id" : user_id,
                                        "role_id" : role,
                                        "token" : token
                                        }
                                    ),
                                )
                            return {
                                "statusCode" : statusCode,
                                "headers" : response_headers,
                                "body" : json.dumps(response),
                                "isBase64Encoded": False,
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
