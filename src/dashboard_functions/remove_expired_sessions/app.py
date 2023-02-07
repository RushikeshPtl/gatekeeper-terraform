import json
import boto3
from datetime import datetime, timedelta
import os

def lambda_handler(event, context):
    s3_client = boto3.client('s3')
    bucket = os.environ["STAGE_S3_BUCKET"] if os.environ["ENVIRONMENT"] == "dev" else os.environ["PROD_S3_BUCKET"]
    try:
        response = s3_client.get_object(
                    Bucket=bucket,
                    Key="session_json"
                    )
        session_json = json.load(response["Body"])
    except:
        session_json={}
    if session_json:
        expired_keys  = []
        for key, value in session_json.items():
            if datetime.strptime(value["expiry"], "%Y-%m-%d %H:%M:%S.%f") < datetime.now():
                expired_keys.append(key)
            else:
                continue
        for k in expired_keys:
            del session_json[k]
        response = s3_client.put_object(
                Body = json.dumps(session_json),
                Bucket = bucket,
                Key = "session_json"
            )
        return {
            "statusCode" : 200,
            "msg" : "Expired sessions removed successfully"
        }
    else:
        return {
            "statusCode" : 200,
            "msg" : "No existing sessions"
        }