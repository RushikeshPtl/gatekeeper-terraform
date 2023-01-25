import json
import boto3
import os
import logging
from sqlalchemy import create_engine, MetaData, Table, update


logger = logging.getLogger()
logger.setLevel(logging.INFO)

response_headers = {
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "DELETE, OPTIONS",
}


class ApiError(Exception):
    def __init__(self, code, message="Api Error"):
        self.code = code
        self.message = message
        super().__init__(self.message)


def create_db_engine_and_meta(db_credentials):
    engine = create_engine(
        "postgresql+psycopg2://{}:{}@{}/{}".format(
            db_credentials["username"],
            db_credentials["password"],
            db_credentials["host"],
            db_credentials["db"]
        )
    )
    meta = MetaData(engine)

    return engine, meta


def authorize(token):
    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_USER_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"type": "session_token", "token": token}),
    )
    payload = json.load(response["Payload"])
    allowed_permissions = payload.get("permissions", {}).get("Allowed", [])
    is_master = payload.get("is_master", False)
    if 'error' in payload:
        raise ApiError(500, 'Error while accessing token')

    if 'user_id' not in payload:
        raise ApiError(500, str(payload["msg"]))

    if not is_master and "delete_organization" not in allowed_permissions:
        raise ApiError(401, 'Unauthorized user')


def validate_body(body):
    if 'token' not in body.keys() or not body['token']:
        raise ApiError(401, 'Token is required')


def get_organization_id(event):
    return event["pathParameters"]["id"]


def get_database_secrets():
    lambda_client = boto3.client('lambda')
    response = lambda_client.invoke(
        FunctionName=os.environ['GET_SECRET_ARN'],
        InvocationType='RequestResponse',
        Payload=json.dumps({'secret_type': 'Database Credentials'}),
    )

    payload = json.load(response['Payload'])
    if 'error' in payload:
        raise ApiError(
            500, f"accessing secrets manager got an error: {str(payload['error'])}")

    return payload['credentials']


def create_table(name, meta, engine):
    tb = Table(
        name,
        meta,
        autoload=True,
        autoload_with=engine
    )

    return tb


def get_tokens_bucket():
    s3_client = boto3.client("s3")
    bucket = os.environ["STAGE_S3_BUCKET"] if os.environ["ENVIRONMENT"] == "DEV" else os.environ["PROD_S3_BUCKET"]

    return s3_client, bucket


def revoke_db_token(token_type, org_id, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)
    table = create_table(token_type, meta, engine)

    try:
        stmt = (
            update(table).
            where(table.columns.organization_id == org_id).
            values(archived=1)
        )
        connection = engine.connect()
        connection.execute(stmt)
    except Exception as e:
        raise ApiError(
            500, f"Faied to revoke organization's {token_type} token: {e}")


def revoke_s3_token(org_id):
    s3_client, bucket = get_tokens_bucket()
    s3_key = "System/Organizations/{}/tokens.json".format(org_id)
    token_data = {}

    try:
        s3_client.put_object(
            Body=json.dumps(token_data, sort_keys=True, indent=4),
            Bucket=bucket,
            Key=s3_key
        )
    except Exception as e:
        raise ApiError(
            500, f'Faied to revoke token for organization: {org_id} in s3: {e}')


def archive_organization(org_id, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)
    table = create_table("organizations", meta, engine)

    try:
        stmt = (
            update(table).
            where(table.columns.id == org_id).
            values(archived=1)
        )
        connection = engine.connect()
        connection.execute(stmt)
    except Exception as e:
        raise ApiError(
            500, f'Faied to archive for organization {org_id}: {e}')


def archive_organization_data_type(data_type, org_id, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)
    table = create_table(data_type, meta, engine)

    try:
        stmt = (
            update(table).
            where(table.columns.organization_id == org_id).
            values(archived=1)
        )
        connection = engine.connect()
        connection.execute(stmt)
    except Exception as e:
        raise ApiError(
            500, f'Faied to archive {data_type} for organization {org_id}: {e}')


def lambda_handler(event, context):
    if 'source' in event and event['source'] == 'aws.events':
        return {
            'msg': 'Warm up triggered..............'
        }

    try:
        body = json.loads(event['body'])
        validate_body(body)
        authorize(body['token'])

        db_credentials = get_database_secrets()
        org_id = get_organization_id(event)
        revoke_db_token("referral_tokens", org_id, db_credentials)
        revoke_db_token("documentation_tokens", org_id, db_credentials)
        revoke_s3_token(org_id)
        archive_organization_data_type(
            "organization_amd_codes", org_id, db_credentials)
        archive_organization_data_type(
            "organization_contacts", org_id, db_credentials)
        archive_organization(org_id, db_credentials)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "statusCode": 200,
                "organization_id": org_id,
                "msg": "Archived successfully"
            }),
            "headers": response_headers,
        }
    except ApiError as e:
        logger.error(e)
        return {
            "statusCode": e.code,
            "headers": response_headers,
            "body": json.dumps({
                "statusCode": e.code,
                "msg": e.message,
            })
        }