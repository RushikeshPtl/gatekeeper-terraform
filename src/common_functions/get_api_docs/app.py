import boto3
import logging
import os
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

response_headers = {
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS"
    }

def lambda_handler(event, context):
    bucket = os.environ["STAGE_BUCKET_NAME"] if os.environ["ENVIRONMENT"] == "DEV" else os.environ["PROD_BUCKET_NAME"]
    key = os.environ["KEY"]

    s3 = boto3.client('s3')

    try:
        response = s3.generate_presigned_url(
            'get_object',
            Params = {
                'Bucket': bucket,
                'Key': key}
        )
        return {
            "statusCode" : 200,
            "headers" : response_headers,
            "body" : json.dumps({
                "statusCode": 200,
                "url": response,
                "msg": "success",
            }),
            "isBase64Encoded": False,
        }
    except Exception as e:
        logger.error(e)
        return {
            "statusCode" : 500,
            "headers" : response_headers,
            "body" : json.dumps({
                "statusCode": 500,
                "msg": "Error while fetching url",
            }),
            "isBase64Encoded": False,
        }
