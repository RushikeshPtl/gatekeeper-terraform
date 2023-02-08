import json
import boto3
from botocore.exceptions import ClientError
import os
import uuid

lambda_client = boto3.client("lambda")

class ApiError(Exception):
    def __init__(self, code, message="Api Error"):
        self.code = code
        self.message = message
        super().__init__(self.message)

def get_tokens_bucket():
    s3_client = boto3.client("s3")
    bucket    = os.environ["STAGE_BUCKET_NAME"] if os.environ["ENVIRONMENT"] == "dev" else os.environ["PROD_BUCKET_NAME"]

    return s3_client, bucket

def lambda_handler(event, context):

    s3_client, bucket = get_tokens_bucket()
    s3_key            = "form_validator.json"
    token             = uuid.uuid4().hex
    token_data        = {
                            "token": token,
                        }
    try:
        s3_client.put_object(
            Body   = json.dumps(token_data, sort_keys = True, indent = 4),
            Bucket = bucket,
            Key    = s3_key
        )
        return token_data
    except Exception as e:
        raise ApiError(
            500, f'Faied to create tokens for referral in s3: {e}')
