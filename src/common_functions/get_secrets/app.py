import boto3
from botocore.exceptions import ClientError
import json
import os
from aws_lambda_powertools import Logger
from shared import GateKeeperException


logger = Logger()


DATABASE_CREDENTIALS = "Database Credentials"
UFT_TOKEN = "UFT Token"
AMD_TOKEN = "AMD Token"
AMD_CREDS = "AMD Creds"
REDIS_CREDENTIALS = "Redis Credentials"


VALID_SECRET_TYPES = [
    DATABASE_CREDENTIALS,
    UFT_TOKEN,
    AMD_TOKEN,
    AMD_CREDS,
    REDIS_CREDENTIALS
]


def get_secret_type(event):
    secret_type = event.get("secret_type", "")

    if secret_type not in VALID_SECRET_TYPES:
        raise GateKeeperException(
            400, f"secret_type type must be one of: {VALID_SECRET_TYPES}")

    return secret_type


def get_session_client():
    region_name = os.environ["REGION_NAME"]

    session = boto3.session.Session()
    client = session.client(
        service_name="secretsmanager",
        region_name=region_name,
    )

    return client


def get_secret_value(client, secret_id):
    response = client.get_secret_value(
        SecretId=secret_id)
    secret = json.loads(response["SecretString"])

    return secret


@logger.inject_lambda_context
def lambda_handler(event, context):
    """
        Function Name : GetSecrets

        - Creats the secret manager client to get the secrets needed to process the requests such as DB credentials, tokens etc

        Parameters:
        -----
        event : dict with secret type

        Response:
        -----
        dict
    """
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg": "Warm up triggered.............."
        }

    try:
        secret_type = get_secret_type(event=event)
        client = get_session_client()

        if secret_type == DATABASE_CREDENTIALS:
            secret = get_secret_value(
                client=client,
                secret_id=os.environ["DATABASE_SECRET_NAME"]
            )

            credentials = {
                "username":  secret["username"],
                "password": secret["password"],
                "host": secret["host"],
                "db": os.environ["DATABASE_NAME"]
            }

            return {
                "status": 200,
                "credentials": credentials
            }

        if secret_type == UFT_TOKEN:
            secret = get_secret_value(
                client=client,
                secret_id=os.environ["UFT_TOKEN"]
            )

            return {
                "status": 200,
                "token": secret["token"]
            }

        if secret_type == AMD_TOKEN:
            secret = get_secret_value(
                client=client,
                secret_id=os.environ["AMD_SECRET_NAME"]
            )

            return {
                "status": 200,
                "token": secret["token"],
                "webserver": secret["webserver"],
                "pmapiredirecturl": secret["pmapiredirecturl"]
            }

        if secret_type == AMD_CREDS:
            secret = get_secret_value(
                client=client,
                secret_id=os.environ["AMD_CREDS_NAME"]
            )

            credentials = {
                "officecode": secret["officecode"],
                "username": secret["username"],
                "password": secret["password"]
            }

            return {
                "status": 200,
                "credentials": credentials
            }

        if secret_type == REDIS_CREDENTIALS:
            secret = get_secret_value(
                client=client,
                secret_id=os.environ["REDIS_CREDS_NAME"]
            )

            credentials = {
                "username": secret["username"],
                "password": secret["password"]
            }

            return {
                "status": 200,
                "credentials": credentials
            }
    except GateKeeperException as e:
        logger.error(e)
        return {
            "error_code": e.code,
            "msg": "Error while accessing the credentials",
            "error": e.message,
        }
