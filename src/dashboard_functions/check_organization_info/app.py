import json
import boto3
import os
import logging
from sqlalchemy import create_engine, MetaData, Table, text, select


logger = logging.getLogger()
logger.setLevel(logging.INFO)

response_headers = {
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
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

    if 'error' in payload:
        raise ApiError(500, 'Error while accessing token')

    if 'user_id' not in payload:
        raise ApiError(500, str(payload["msg"]))


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


def get_field_and_value(event):
    if "queryStringParameters" not in event and event["queryStringParameters"] == None:
        raise ApiError(400, f"Invalid parameters")

    field = event["queryStringParameters"].get("field", "")
    value = event["queryStringParameters"].get("value", "")

    if not field or not value:
        raise ApiError(400, f"Invalid parameters")

    fields = ['abbr', 'subdomain']
    if field not in fields:
        raise ApiError(400, f"Field must be one of: {fields}")

    return field, value


def check_organization_info(field, value, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)

    organizations = Table(
        "organizations",
        meta,
        autoload=True,
        autoload_with=engine
    )

    try:
        stmt = select([
            organizations.columns.id,
            organizations.columns.title,
        ]).where(text(
            '''
                ({}  = '{}')
            '''.format(field, value)
        ))

        connection = engine.connect()
        result = connection.execute(stmt).fetchone()

        return True if result else False
    except Exception as e:
        raise ApiError(500, f'Faied to check organization: {e}')


def lambda_handler(event, context):
    if 'source' in event and event['source'] == 'aws.events':
        return {
            'msg': 'Warm up triggered..............'
        }

    try:
        authorize(event["queryStringParameters"].get("token", ""))
        db_credentials = get_database_secrets()
        field, value = get_field_and_value(event)
        existing = check_organization_info(field, value, db_credentials)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "statusCode": 200,
                "field": field,
                "value": value,
                "existing": existing,
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

