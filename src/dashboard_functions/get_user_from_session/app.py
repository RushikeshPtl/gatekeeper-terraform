import json
import boto3
from datetime import datetime
import os

def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    token=event.get("token","")
    token_type=event.get("type","")
    client = boto3.client('s3')
    s3_key="first_login_json" if token_type == "first_login_token" else "session_json"
    bucket = os.environ["STAGE_S3_BUCKET"] if os.environ["ENVIRONMENT"] == "dev" else os.environ["PROD_S3_BUCKET"]
    try:
        response = client.get_object(
                            Bucket=bucket,
                            Key=s3_key
                            )

        session_json = json.load(response["Body"])
        session = session_json.get(token, None)
        if not session:
            return {
                    "statusCode": 200,
                    "msg": "Please send valid token",
                    }
        elif s3_key == "session_json" and datetime.strptime(session["expiry"], "%Y-%m-%d %H:%M:%S.%f") < datetime.now():
            return {
                "statusCode": 200,
                "msg": "Session Expired",
            }
        elif s3_key == "first_login_json":
            user_id = session
            permissions = None
            response = {
                "statusCode" : 200,
                "msg" : "User id fetched",
                "user_id" : user_id
            }
        else:
            user_id = session["user_id"]
            is_master = session.get("is_master", False)
            role = session.get("role", None)
            role_level = session.get("role_level", None)
            try:
                permission_response = client.get_object(
                                    Bucket=bucket,
                                    Key="System/Users/{}/user_permissions.json".format(int(user_id))
                                    )
                permissions = json.load(permission_response["Body"])
            except:
                permissions = {}
            response = {
                "statusCode" : 200,
                "msg" : "User id fetched",
                "user_id" : user_id,
                "is_master" : is_master,
                "role" : role,
                "role_level" : role_level,
                "permissions" : permissions
            }
            lambda_client = boto3.client("lambda")
            s3_response = lambda_client.invoke(
                FunctionName=os.environ["UPDATE_S3_ARN"],
                InvocationType="Event",
                Payload=json.dumps({
                    "token_type": "session_token",
                    "token": token,
                    "user_id":user_id,
                    "s3_type":"add",
                    "is_master" : is_master,
                    "role" : role,
                    "role_level" : role_level
                }),
            )
        return response
    except:
        return {
            "statusCode": 500,
            "msg": "Something went wrong with s3",
        }