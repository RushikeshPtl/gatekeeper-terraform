import json
import boto3
import os

def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    response_headers = {
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET",
                    }

    token = event["queryStringParameters"].get("token","") if "queryStringParameters" in event and event["queryStringParameters"] != None else ""

    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
                    FunctionName=os.environ["UPDATE_S3_ARN"],
                    InvocationType="RequestResponse",
                    Payload=json.dumps({"token_type": "session_token", "token": token, "s3_type":"delete" }),
                )
    payload = json.load(response["Payload"])

    if "error" in payload:
        return {
                "statusCode": 200,
                "body" : json.dumps({
                    "statusCode": 200,
                    "msg": payload["error"],
                }),
                "isBase64Encoded": False,
            }
    else:
        return {
        "statusCode": 200,
        "headers": response_headers,
        "body": json.dumps({
            "msg": "logged out successfully",
        }),
        "isBase64Encoded": False,
    }