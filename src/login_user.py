import json
from sqlalchemy import create_engine, select, MetaData, Table, text
import bcrypt
import uuid
from random import randint
import boto3
import os

def is_json(json_data):
    try:
        if not isinstance(json_data, dict):
            json.loads(json_data)
        else:
            return True
    except ValueError:
        return False
    return True

def escape_apostrophe(string):
    items = string.split("'")
    new_string = items[0]
    for i in items[1:]:
        new_string += "''" + i
    return new_string

def lambda_handler(event, context):
    response_headers = {
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "POST",
                    }

    if is_json(event):
        if not isinstance(event, dict):
            event = json.loads(event)
        if "source" in event and event["source"] == "aws.events":
            print("Warm up triggered..............")
            return {
                "msg" : "Warm up triggered.............."
            }
        event = json.loads(event["body"])
        lambda_client = boto3.client("lambda")
        response = lambda_client.invoke(
            FunctionName=os.environ["GET_SECRET_ARN"],
            InvocationType="RequestResponse",
            Payload=json.dumps({"secret_type": "Database Credentials"}),
        )
        payload = json.load(response["Payload"])
        if "error" in payload:
            return {
                "statusCode": 500,
                "body" : json.dumps({
                    "statusCode": 500,
                    "msg": "error while accessing secrets manager",
                    "error": payload["error"]
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

            connection = engine.connect()
            metadata = MetaData(engine)

            users = Table(
                "users",
                metadata,
                autoload=True,
                autoload_with=engine
            )

            roles = Table(
                "roles",
                metadata,
                autoload = True,
                autoload_with = engine
            )

            username = event.get("username","")
            password = event.get("password","")

            if username=="" or password == "":
                return {
                    "statusCode": 200,
                    "headers": response_headers,
                    "body": json.dumps({
                        "statusCode": 200,
                        "msg": "Username or Password cannot empty...",
                    }),
                    "isBase64Encoded": False,
                }
            join = users.join(roles, users.columns.role_id == roles.columns.id)
            stmt = select([
                users.columns.id,
                users.columns.username,
                users.columns.password,
                users.columns.email,
                users.columns.is_verified,
                users.columns.is_master,
                roles.columns.role,
                roles.columns.role_level
            ]).select_from(join).where(text(
                '''
                    (username  = '{}'
                    OR email = '{}'
                    )
                    AND (archived = 'False')
                '''.format(escape_apostrophe(username), escape_apostrophe(username))))

            connection = engine.connect()
            try:
                results = connection.execute(stmt).fetchall()
            except Exception as e:
                return {
                    "statusCode": 200,
                    "headers": response_headers,
                    "body":json.dumps({
                        "statusCode": 200,
                        "msg": "Something went wrong",
                        "error_response":e
                    }),
                    "isBase64Encoded": False,
                }

            if len(results) != 0:
                user = results[0]
                db_pass = user["password"]
                bytepass = bytes(db_pass, "utf-8")
                userBytes = password.encode("utf-8")
                authenticated = bcrypt.checkpw(userBytes, bytepass)
            else:
                return {
                    "statusCode": 200,
                    "headers": response_headers,
                    "body":json.dumps({
                        "statusCode": 200,
                        "msg": "Please enter valid credentials.",
                    }),
                    "isBase64Encoded": False,
                }

            if not authenticated:
                return {
                    "statusCode": 200,
                    "headers": response_headers,
                    "body":json.dumps({
                        "statusCode": 200,
                        "msg": "Please enter valid credentials.",
                    }),
                    "isBase64Encoded": False,
                }
            elif authenticated:
                auth_token = uuid.uuid4().hex.upper()
                user_id = user["id"]
                is_master = user["is_master"]
                role = user["role"]
                role_level = user["role_level"]
                lambda_client = boto3.client("lambda")
                response = lambda_client.invoke(
                    FunctionName=os.environ["UPDATE_S3_ARN"],
                    InvocationType="RequestResponse",
                    Payload=json.dumps({
                        "token_type": "session_token",
                        "token": auth_token,
                        "user_id":user_id,
                        "s3_type":"add",
                        "is_master" : is_master,
                        "role" : role,
                        "role_level" : role_level
                    }),
                )
                payload = json.load(response["Payload"])
                if "error" in payload:
                    return {
                        "statusCode": 500,
                        "body" : json.dumps({
                            "statusCode": 500,
                            "msg": "error while accessing token"
                        }),
                        "isBase64Encoded": False,
                    }

                if user["is_verified"] == True:
                    return {
                        "statusCode":200,
                        "headers": response_headers,
                        "body": json.dumps({
                                "statusCode":200,
                                "msg":"Logged in successfully",
                                "is_master":is_master,
                                "token":auth_token
                            }),
                        "isBase64Encoded": False,
                        }

                else:
                    otp = randint(100000, 999999)
                    email = user["email"]
                    response = lambda_client.invoke(
                        FunctionName=os.environ["SEND_EMAIL_ARN"],
                        InvocationType="Event",
                        Payload=json.dumps({
                            "type": "Verify Mail",
                            "email": email,
                            "name": user["username"],
                            "otp": otp}),
                    )

                    return {
                        "statusCode":200,
                        "headers": response_headers,
                        "body": json.dumps({
                                "statusCode":200,
                                "msg":"logged in successfully, Please verify email",
                                "otp":otp,
                                "token":auth_token
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

