import json
import boto3
from datetime import datetime, timedelta
import os


def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg": "Warm up triggered.............."
        }
    token = event.get("token", "")
    user_id = event.get("user_id", "")
    s3_type = event.get("s3_type", "")
    token_type = event.get("token_type", "")
    s3_client = boto3.client('s3')
    s3_key = "first_login_json" if token_type == "first_login_token" else "session_json"
    bucket = os.environ["S3_BUCKET"]
    if not token:
        return {
            "statusCode": 200,
            "error": "Please send valid token"
        }

    try:
        response = s3_client.get_object(
            Bucket=bucket,
            Key=s3_key
        )
        session_json = json.load(response["Body"])
    except:
        session_json = {}

    if s3_type == "add":
        try:
            user_id_token = [key for key,
                             value in session_json.items() if value == user_id]
            if len(user_id_token) > 0:
                del session_json[user_id_token[0]]
            if s3_key == "session_json":
                is_master = event.get("is_master", False)
                role = event.get("role", None)
                role_level = event.get("role_level", None)
                session_json[token] = {
                    "user_id": user_id,
                    "is_master": is_master,
                    "role": role,
                    "role_level": role_level,
                    "expiry": str(datetime.now() + timedelta(hours=1))
                }
            else:
                session_json[token] = user_id
            response = s3_client.put_object(
                Body=json.dumps(session_json, sort_keys=True, indent=4),
                Bucket=bucket,
                Key=s3_key
            )
            return {
                "statusCode": 200,
                "msg": "token added successfully",
                "user_id": user_id
            }
        except:
            return {
                "statusCode": 200,
                "error": "Something went wrong with s3",

            }
    elif s3_type == "delete":
        try:
            if token in session_json:
                del session_json[token]
                response = s3_client.put_object(
                    Body=json.dumps(session_json, sort_keys=True, indent=4),
                    Bucket=bucket,
                    Key=s3_key
                )
            else:
                return {
                    "statusCode": 200,
                    "error": "Unknown Session"
                }
            return {
                "statusCode": 200,
                "msg": "token deleted successfully",
            }

        except:
            return {
                "statusCode": 200,
                "error": "Something went wrong with s3",
            }
    else:
        return {
            "statusCode": 200,
            "error": "Invalide type",
        }
