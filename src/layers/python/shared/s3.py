import boto3
import json
from error import GateKeeperException


def get_json_object(bucket, key):
    s3_client = boto3.client('s3')
    try:
        response = s3_client.get_object(
            Bucket=bucket,
            Key=key
        )

        json_body = json.load(response["Body"])

        return json_body
    except Exception as e:
        raise GateKeeperException(code=500, message=f"{e}")


def put_json_object(json_object, bucket, key):
    s3_client = boto3.client('s3')
    try:
        s3_client.put_object(
            Body=json.dumps(json_object, sort_keys=True, indent=4),
            Bucket=bucket,
            Key=key
        )
    except Exception as e:
        raise GateKeeperException(code=500, message=f"{e}")
