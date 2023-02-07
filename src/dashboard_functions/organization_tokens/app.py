import json
import boto3
import os
import logging
from sqlalchemy import create_engine, MetaData, Table, update, select
from datetime import timedelta, date
import uuid


logger = logging.getLogger()
logger.setLevel(logging.INFO)
lambda_client = boto3.client("lambda")
response_headers = {
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, DELETE, OPTIONS",
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

database_credentials = get_database_secrets()
engine, meta = create_db_engine_and_meta(db_credentials=database_credentials)

def get_http_method(event):
    return event.get("httpMethod")


def get_organization_id(event):
    if not event["pathParameters"]["org_id"]:
        raise ApiError(400, f"Organization ID is required")
    return event["pathParameters"]["org_id"]


def get_token_id(event):
    if not event["pathParameters"]["token_id"]:
        raise ApiError(400, f"Token ID is required")
    return event["pathParameters"]["token_id"]


def get_token(event):
    return event["queryStringParameters"].get("token", "")


def create_table(name):
    tb = Table(
        name,
        meta,
        autoload=True,
        autoload_with=engine
    )

    return tb

def send_notification(org_id, token_data):
    organization_contacts = create_table("organization_contacts")
    organizations = create_table("organizations")
    connection = engine.connect()
    join = organization_contacts.join(organizations, organization_contacts.columns.organization_id == organizations.columns.id)
    stmt = select([
        organizations.columns.title,
        organization_contacts.columns.contact_person,
        organization_contacts.columns.phone,
        organization_contacts.columns.mobile,
        organization_contacts.columns.email
    ]).select_from(join).where(
        organization_contacts.columns.organization_id == org_id,
        organization_contacts.columns.archived == False
    )
    try:
        result = connection.execute(stmt).fetchone()
    except Exception as e:
        ApiError(500, "Tokens Changed Successfully, SOmething went wrong while sending notification")
    send_email = lambda_client.invoke(
        FunctionName=os.environ["SEND_EMAIL_ARN"],
        InvocationType="Event",
        Payload=json.dumps({
            "type": "Organization Token",
            "organization" : result["title"],
            "email": result["email"],
            "name": result["contact_person"],
            "mobile": result["mobile"],
            "token_data" : token_data
            }
        ),
    )
    logger.info('Notification Sent')
    return {
        "msg" : "Notification Sent Successfully"
    }

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

    if not is_master and "edit_organization" not in allowed_permissions:
        raise ApiError(401, 'Unauthorized user')


def validate_body(body):
    token_type = body.get("token_type", "")
    if not token_type:
        raise ApiError(400, f"Token type is required")

    token_types = ['documentation', 'referral']
    if token_type not in token_types:
        raise ApiError(400, f"Token type must be one of: {token_types}")


def get_tokens_bucket():
    s3_client = boto3.client("s3")
    bucket = os.environ["STAGE_S3_BUCKET"] if os.environ["ENVIRONMENT"] == "dev" else os.environ["PROD_S3_BUCKET"]

    return s3_client, bucket


def get_s3_token(org_id):
    try:
        s3_client, bucket = get_tokens_bucket()
        s3_key = "System/Organizations/{}/tokens.json".format(org_id)
        response = s3_client.get_object(
            Bucket=bucket,
            Key=s3_key
        )
        tokens = json.load(response["Body"])
        if not tokens:
            return {}

        return tokens
    except:
        return {}


def sync_s3_token(org_id, new_token, token_type):
    s3_client, bucket = get_tokens_bucket()
    s3_key = "System/Organizations/{}/tokens.json".format(org_id)
    
    try:
        token_data = get_s3_token(org_id)
        field_to_update = "documentation_token" if token_type == "documentation_tokens" else "referral_token"
        token_data[field_to_update] = new_token

        s3_client.put_object(
            Body=json.dumps(token_data, sort_keys=True, indent=4),
            Bucket=bucket,
            Key=s3_key
        )
        return token_data
    except Exception as e:
        raise ApiError(
            500, f'Faied to create tokens for organization: {org_id} in s3: {e}')


def revoke_all_db_token(org_id, token_type):
    table = create_table(token_type)

    try:
        stmt = (
            update(table).
            where(table.columns.organization_id == int(org_id), table.columns.archived == False).
            values(archived=True)
        )
        connection = engine.connect()
        connection.execute(stmt)
    except Exception as e:
        raise ApiError(
            500, f"Faied to revoke organization's {token_type} token: {e}")


def revoke_db_token(token_type, token_id):
    table = create_table(token_type)

    try:
        stmt = (
            update(table).
            where(table.columns.id == int(token_id)).
            values(archived=1)
        )
        connection = engine.connect()
        connection.execute(stmt)
    except Exception as e:
        raise ApiError(
            500, f"Faied to revoke organization's {token_type} token: {e}")


def create_db_token(org_id, token_type, custom_token = None, set_validity = False, validity = 30):
    table = create_table(token_type)

    try:
        token = uuid.uuid4().hex if (custom_token and custom_token.isspace()) or not custom_token else custom_token.replace(" ","")
      
        validity = validity if set_validity and validity else 30 if set_validity and not validity else None
        expiry_date = date.today() + timedelta(days=int(validity)) if validity else None

        doc_token = table.insert().values(
            organization_id=org_id,
            token=token,
            expiry_date=expiry_date
        )

        connection = engine.connect()
        result = connection.execute(doc_token)
        token_id = result.inserted_primary_key[0]

        return {
            "id": token_id,
            "token": token,
            "expiry_date": expiry_date.isoformat() if expiry_date else None
        }
    except Exception as e:
        raise ApiError(
            500, f"Faied to create organization's {token_type} token: {e}")


def revoke_token(org_id, token_type, token_id):
    try:
        revoke_db_token(token_type, token_id)
        token_data = sync_s3_token(org_id, {}, token_type)
        send_notification(org_id, token_data)
    except ApiError as e:
        raise e


def create_token(org_id, token_type, custom_token = None, set_validity = False, validity = 30):
    try:
        # revokes old tokens if exists before creates new one
        revoke_all_db_token(org_id, token_type)
        new_token = create_db_token(org_id, token_type, custom_token, set_validity, validity)
        token_data = sync_s3_token(org_id, new_token, token_type)
        send_notification(org_id, token_data)
    except ApiError as e:
        raise e


def execute_create_token(event):
    try:
        org_id = get_organization_id(event)
        body = json.loads(event["body"])
        token_type = "documentation_tokens" if body.get('token_type', "") == "documentation" else "referral_tokens"
        custom_token = body.get("custom_token", None)
        set_validity = body.get("set_validity", False)
        validity = body.get("validity", 30)
        create_token(org_id, token_type, custom_token, set_validity, validity)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "statusCode": 200,
                "token_type": token_type,
                "msg": f"creates token of type {token_type} for organization {org_id} successfully"
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

def execute_revoke_token(event):
    try:
        org_id = get_organization_id(event)
        body = json.loads(event["body"])
        token_type = "documentation_tokens" if body.get('token_type', "") == "documentation" else "referral_tokens"
        token_id = get_token_id(event)
        revoke_token(org_id, token_type, token_id)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "statusCode": 200,
                "token_type": token_type,
                "msg": f"revokes token of type {token_type} for organization {org_id} successfully"
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


def lambda_handler(event, context):
    if 'source' in event and event['source'] == 'aws.events':
        return {
            'msg': 'Warm up triggered..............'
        }
    authorize(get_token(event))
    method = get_http_method(event)
    body = json.loads(event['body'])
    validate_body(body)

    if method == 'POST':
        return execute_create_token(event)
    elif method == 'DELETE':
        return execute_revoke_token(event)
    else:
        return {
            "statusCode": 405,
            "headers": response_headers,
            "body": json.dumps({
                "statusCode": 405,
                "msg": "Method not allowed",
            })
        }