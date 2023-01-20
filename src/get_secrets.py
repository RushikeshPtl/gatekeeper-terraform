import boto3
from botocore.exceptions import ClientError
import json
import os


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
    secret_type = event["secret_type"]
    credentials = {}
    region_name = os.environ["REGION_NAME"]
    session = boto3.session.Session()
    client = session.client(
        service_name="secretsmanager", region_name=region_name)
    try:
        if secret_type == "Database Credentials":
            secret_name = os.environ["DATABASE_SECRET_NAME"]
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name)
            secret = json.loads(get_secret_value_response["SecretString"])
            credentials["username"] = secret["username"]
            credentials["password"] = secret["password"]
            credentials["host"] = secret["host"]
            credentials["db"] = os.environ["DATABASE_NAME"]
            print(credentials)
            return {
                "status": 200,
                "credentials": credentials
            }
        elif secret_type == "UFT Token":
            secret_name = os.environ["UFT_TOKEN"]
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name)
            secret = json.loads(get_secret_value_response["SecretString"])
            return {
                "status": 200,
                "token": secret["token"]
            }
        elif secret_type == "AMD Token":
            secret_name = os.environ["AMD_SECRET_NAME"]
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name)
            secret = json.loads(get_secret_value_response["SecretString"])
            return {
                "status": 200,
                "token": secret["token"],
                "webserver": secret["webserver"],
                "pmapiredirecturl": secret["pmapiredirecturl"]
            }
        elif secret_type == "AMD Creds":
            secret_name = os.environ["AMD_CREDS_NAME"]
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name)
            secret = json.loads(get_secret_value_response["SecretString"])
            credentials["officecode"] = secret["officecode"]
            credentials["username"] = secret["username"]
            credentials["password"] = secret["password"]
            return {
                "status": 200,
                "credentials": credentials
            }
        elif secret_type == "Redis Credentials":
            secret_name = "ElastiCacheCreds"
            get_secret_value_response = client.get_secret_value(
                SecretId=secret_name)
            secret = json.loads(get_secret_value_response["SecretString"])
            credentials["username"] = secret["username"]
            credentials["password"] = secret["password"]
            return {
                "status": 200,
                "credentials": credentials
            }
    except ClientError as e:
        return {
            "error_code": 500,
            "msg": "Error while accessing the credentials",
            "error": e,
        }
