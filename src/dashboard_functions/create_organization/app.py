import json
import boto3
import os
import logging
from sqlalchemy import create_engine, MetaData, Table, select, update
from datetime import timedelta, date
import uuid
import re


logger = logging.getLogger()
logger.setLevel(logging.INFO)

response_headers = {
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, PUT, OPTIONS",
}
lambda_client = boto3.client("lambda")

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

db_credentials = get_database_secrets()
engine, meta = create_db_engine_and_meta(db_credentials)

def authorize(token, action):
    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_USER_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"type": "session_token", "token": token}),
    )
    payload = json.load(response["Payload"])
    allowed_permissions = payload.get("permissions", {}).get("Allowed", [])
    is_master = payload.get("is_master", False)
    permission = f"{action}_organization"
    if 'error' in payload:
        raise ApiError(500, 'Error while accessing token')

    if 'user_id' not in payload:
        raise ApiError(500, str(payload["msg"]))

    if not is_master and permission not in allowed_permissions:
        raise ApiError(401, 'Unauthorized user')


def validate_email(email):
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    if (re.fullmatch(regex, email)):
        return True
    else:
        return False


def validate_body(body):
    if 'title' not in body.keys() or not body['title']:
        raise ApiError(400, 'Title is required')

    if 'abbr' not in body.keys() or not body['abbr']:
        raise ApiError(400, 'Abbr is required')

    if 'subdomain' not in body.keys() or not body['subdomain']:
        raise ApiError(400, 'Subdomain is required')

    if 'contact_person' not in body.keys() or not body['contact_person']:
        raise ApiError(400, 'Contact person is required')

    if 'phone' not in body.keys() or not body['phone']:
        raise ApiError(400, 'Phone is required')

    if 'mobile' not in body.keys() or not body['mobile']:
        raise ApiError(400, 'Mobile is required')

    if 'email' not in body.keys() or not body['email']:
        raise ApiError(400, 'Email is required')

    if not validate_email(body['email']):
        raise ApiError(400, f"Invalid Email: {body['email']}")

    if 'referral_status' not in body.keys() or not body['referral_status']:
        raise ApiError(400, 'Referral status is required')

    if 'referral_provider_code' not in body.keys() or not body['referral_provider_code']:
        raise ApiError(400, 'Referral provider code is required')

    if 'financial_class' not in body.keys() or not body['financial_class']:
        raise ApiError(400, 'Financial class code is required')


def get_http_method(event):
    return event.get("httpMethod")


def get_organization_id(event):
    return event["pathParameters"]["id"]
    

def get_token(event):
    if not event["queryStringParameters"] or not event["queryStringParameters"].get("token"):
        raise ApiError(401, 'Unauthorized user')
    return event["queryStringParameters"].get("token")

def create_table(name):
    tb = Table(
        name,
        meta,
        autoload=True,
        autoload_with=engine
    )

    return tb

def send_notification(org_data, token_data):
    send_email = lambda_client.invoke(
        FunctionName=os.environ["SEND_EMAIL_ARN"],
        InvocationType="Event",
        Payload=json.dumps({
            "type": "Organization Token",
            "organization" : org_data["title"],
            "email": org_data["email"],
            "name": org_data["name"],
            "mobile": org_data["mobile"],
            "token_data" : token_data
            }
        ),
    )
    logger.info('Notification Sent')
    return {
        "msg" : "Notification Sent Successfully"
    }

def create_organization(data):
    organizations = create_table("organizations")

    try:
        insert_org = organizations.insert().values(
            title=data['title'],
            abbr=data['abbr'].lower(),
            subdomain=data['subdomain'].lower()
        )

        connection = engine.connect()
        result = connection.execute(insert_org)
        connection.close()

        org_id = result.inserted_primary_key[0]
        return org_id
    except Exception as e:
        raise ApiError(500, f'Faied to create organization: {e}')


def check_organization(org_id):
    organizations = create_table("organizations")

    try:
        stmt = (
            select([organizations.columns.id]).
            where(
                organizations.columns.id == int(org_id)
            )
        )

        connection = engine.connect()
        org_data = connection.execute(stmt).fetchone()
        connection.close()

        if not org_data:
            raise ApiError(404, f'Could not found organization id {org_id}')
    except Exception as e:
        raise ApiError(500, f'Faied to fetch organization: {e}')


def update_organization(data, org_id):
    organizations = create_table("organizations")

    try:
        stmt = (
            update(organizations).
            where(organizations.columns.id == int(org_id)).
            values(
                title=data['title'],
                abbr=data['abbr'],
                subdomain=data['subdomain']
            )
        )

        connection = engine.connect()
        connection.execute(stmt)
        connection.close()
    except Exception as e:
        raise ApiError(500, f'Faied to update organization: {e}')


def create_db_token(token_type, organization_id, custom_token = None, set_validity = False, validity = 30):
    table = create_table(token_type)

    try:
        token = uuid.uuid4().hex if (custom_token and custom_token.isspace()) or not custom_token else custom_token.replace(" ","")
        validity = validity if set_validity and validity else 30 if set_validity and not validity else None
        expiry_date = date.today() + timedelta(days=int(validity)) if validity else None
        ref_token = table.insert().values(
            organization_id=organization_id,
            token=token,
            expiry_date=expiry_date
        )

        connection = engine.connect()
        result = connection.execute(ref_token)
        token_id = result.inserted_primary_key[0]
        connection.close()

        return {
            "id": token_id,
            "token": token,
            "expiry_date": expiry_date.isoformat() if expiry_date else None
        }
    except Exception as e:
        raise ApiError(
            500, f"Faied to create organization's {token_type} token: {e}")


def create_organization_contact(data, org_id):
    organizations = create_table("organization_contacts")

    try:
        insert_org_contact = organizations.insert().values(
            organization_id=org_id,
            contact_person=data['contact_person'],
            phone=data['phone'],
            mobile=data['mobile'],
            email=data['email']
        )

        connection = engine.connect()
        result = connection.execute(insert_org_contact)
        org_contact_id = result.inserted_primary_key[0]
        connection.close()

        return org_contact_id
    except Exception as e:
        raise ApiError(500, f'Faied to create organization contact: {e}')


def update_organization_contact(data, org_id):
    table = create_table("organization_contacts")

    try:
        stmt = (
            update(table).
            where(table.columns.organization_id == int(org_id), table.columns.archived == False).
            values(
                contact_person=data['contact_person'],
                phone=data['phone'],
                mobile=data['mobile'],
                email=data['email']
            )
        )

        connection = engine.connect()
        connection.execute(stmt)
        connection.close()
    except Exception as e:
        raise ApiError(500, f'Faied to update organization contact: {e}')


def create_organization_amd_code(data, org_id):
    organizations = create_table("organization_amd_codes")

    try:
        insert_org_amd = organizations.insert().values(
            organization_id=org_id,
            financial_class=data['financial_class'],
            referral_provider_code=data['referral_provider_code'],
            default_referral_status=data['referral_status'],
        )

        connection = engine.connect()
        result = connection.execute(insert_org_amd)
        org_amd_id = result.inserted_primary_key[0]
        connection.close()

        return org_amd_id
    except Exception as e:
        raise ApiError(500, f'Faied to create organization amd code: {e}')


def update_organization_amd_code(data, org_id):
    table = create_table("organization_amd_codes")

    try:
        stmt = (
            update(table).
            where(table.columns.organization_id == int(org_id), table.columns.archived == False).
            values(
                financial_class=data['financial_class'],
                referral_provider_code=data['referral_provider_code'],
                default_referral_status=data['referral_status'],
            )
        )

        connection = engine.connect()
        connection.execute(stmt)
        connection.close()
    except Exception as e:
        raise ApiError(500, f'Faied to update organization amd code: {e}')


def get_tokens_bucket():
    s3_client = boto3.client("s3")
    bucket = os.environ["STAGE_S3_BUCKET"] if os.environ["ENVIRONMENT"] == "dev" else os.environ["PROD_S3_BUCKET"]
    return s3_client, bucket


def create_s3_token(doc_token, ref_token, org_id):
    s3_client, bucket = get_tokens_bucket()
    s3_key = "System/Organizations/{}/tokens.json".format(org_id)
    token_data = {
        "documentation_token": doc_token,
        "referral_token": ref_token,
    }

    try:
        s3_client.put_object(
            Body=json.dumps(token_data, sort_keys=True, indent=4),
            Bucket=bucket,
            Key=s3_key
        )
        return token_data
    except Exception as e:
        raise ApiError(
            500, f'Faied to create tokens for organization: {org_id} in s3: {e}')


def execute_create_organization(event):
    try:
        body = json.loads(event['body'])
        custom_referral_token = body.get("custom_referral_token", None)
        custom_doc_token = body.get("custom_documentation_token", None)
        set_validity = body.get("set_validity", False)
        validity = body.get("validity", 30)

        validate_body(body)
        authorize(get_token(event), 'create')

        db_credentials = get_database_secrets()
        org_id = create_organization(body)
        org_contact_id = create_organization_contact(
            body,
            org_id
        )
        org_amd_id = create_organization_amd_code(body, org_id)
        ref_token = create_db_token("referral_tokens", org_id, custom_referral_token, set_validity, validity)
        doc_token = create_db_token(
            "documentation_tokens", org_id, custom_doc_token, set_validity, validity)
        org_data = {
            "title": body.get("title", ""),
            "name" : body.get("name", ""),
            "email" : body.get("email", ""),
            "mobile" : body.get("mobile", "")}
        token_data = create_s3_token(doc_token, ref_token, org_id)
        send_notification(org_data, token_data)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "statusCode": 200,
                "organization_id": org_id,
                "organization_contact_id": org_contact_id,
                "referral_token_id": ref_token['id'],
                "documentation_token_id": doc_token['id'],
                "organization_amd_code_id": org_amd_id,
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


def execute_update_organization(event):
    try:
        body = json.loads(event['body'])
        validate_body(body)
        authorize(get_token(event), "edit")

        org_id = get_organization_id(event)

        db_credentials = get_database_secrets()

        check_organization(org_id)
        update_organization(body, org_id)
        update_organization_contact(body, org_id)
        update_organization_amd_code(body, org_id)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "statusCode": 200,
                "organization_id": org_id,
                "msg": 'Updated successfully',
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

    method = get_http_method(event)
    try:
        if method == 'POST':
            return execute_create_organization(event)
        elif method == 'PUT':
            return execute_update_organization(event)
        else:
            return {
                "statusCode": 405,
                "headers": response_headers,
                "body": json.dumps({
                    "statusCode": 405,
                    "msg": "Method not allowed",
                })
            }
    except ApiError as e:
        return {
            "statusCode" : e.code,
            "headers" : response_headers,
            "body" : json.dumps({
                "statusCode" : e.code,
                "msg" : e.message
            })
        }
