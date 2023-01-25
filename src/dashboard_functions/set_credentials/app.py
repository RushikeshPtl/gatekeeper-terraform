import json
# from xmlrpc.client import Boolean
from sqlalchemy import create_engine, MetaData, Table, update, select, text
import boto3
import os
from datetime import datetime
import re
import bcrypt
from sqlalchemy.exc import IntegrityError

def is_json(json_data):
    try:
        if not isinstance(json_data, dict):
            json.loads(json_data)
        else:
            return True
    except ValueError:
        return False
    return True

def lambda_handler(event, context):
    response_headers = {
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS"
    }

    if is_json(event):
        if not isinstance(event, dict):
            event - json.loads(event)
        if "source" in event and event["source"] == "aws.events":
            print("Warm up triggered..............")
            return {
                "msg" : "Warm up triggered.............."
            }
        event = json.loads(event["body"])
        username = event.get("username", "").lower()
        password = event.get("password", "")
        token = event.get("token", "")
        msg = None
        if not password:
            msg = "Password can not be blank"
        elif len(password) < 8 or len(password) > 16:
            msg = "Password length must be 8 to 16 characters"

        if msg:
            return {
                "statusCode" : 400,
                "headers": response_headers,
                "body": json.dumps({
                    "statusCode" : 400,
                    "msg" : msg
                }),
                "isBase64Encoded": False,
            }
        else:
            lambda_client = boto3.client("lambda")
            user_response = lambda_client.invoke(
                FunctionName=os.environ["GET_USER_ARN"],
                InvocationType="RequestResponse",
                Payload=json.dumps({"type": "first_login_token", "token": token}),
            )
            user_payload = json.load(user_response["Payload"])
            error = []
            if "error" in user_payload:
                error.append("Error while fetching the user from session")
            elif "user_id" not in user_payload:
                error.append(user_payload["msg"])
            else:
                user_id = user_payload["user_id"]
            response = lambda_client.invoke(
                FunctionName=os.environ["GET_SECRET_ARN"],
                InvocationType="RequestResponse",
                Payload=json.dumps({"secret_type": "Database Credentials"}),
            )
            payload = json.load(response["Payload"])
            if "error" in payload:
                error.append("Error while accessing secrets manager")
            if error:
                return {
                    "statusCode" : 400,
                    "headers" : response_headers,
                    "body" : json.dumps({
                        "statusCode" : 400,
                        "msg": error
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

                select_user = select([
                            users.columns.id,
                            users.columns.email,
                    ]).where(text(
                            '''
                                (id  = {})
                                AND (archived = 'False')
                            '''.format(user_id)))
                user_data_msg = None
                try:
                    user_data = connection.execute(select_user).fetchone()
                    if user_data:
                        email = user_data["email"]
                    else:
                        user_data_msg = "User Not Found"
                except:
                    user_data_msg = "Something Went Wrong"
                if user_data_msg:
                    return {
                            "statusCode" : 400,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 400,
                                "msg": user_data_msg
                            }),
                            "isBase64Encoded": False,
                        }
                else:
                    if not username:
                        username = email
                    bytes = password.encode('utf-8')
                    salt = bcrypt.gensalt()
                    hash = bcrypt.hashpw(bytes, salt)
                    update_user = update(users).where(users.columns.id == user_id).values(
                        username = username,
                        password = str(hash, 'UTF-8'),
                        is_verified = True
                    )
                    try:
                        result = connection.execute(update_user)
                        statusCode = 200
                        delete_token = lambda_client.invoke(
                            FunctionName=os.environ["UPDATE_S3_ARN"],
                            InvocationType="Event",
                            Payload=json.dumps({
                                "token_type": "first_login_token",
                                "s3_type": "delete",
                                "token" : token,
                                }
                            ),
                        )
                        response = {
                            "statusCode" : 200,
                            "msg" : "Credentials updated successfully...",
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
