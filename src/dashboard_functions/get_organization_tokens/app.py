import json
import boto3
import os
import logging
from sqlalchemy import create_engine, MetaData, Table, select, func
from datetime import datetime

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
    allowed_permissions = payload.get("permissions", {}).get("Allowed", [])
    is_master = payload.get("is_master", False)
    if 'error' in payload:
        raise ApiError(500, 'Error while accessing token')

    if 'user_id' not in payload:
        raise ApiError(500, str(payload["msg"]))

    if not is_master and "view_organization" not in allowed_permissions:
        raise ApiError(401, 'Unauthorized user')


def parse_query_parameters(event):
    token_type = event["queryStringParameters"].get("token_type", "")
    if not token_type:
        raise ApiError(400, f"Token type is required")

    token_types = ['documentation', 'referral']
    if token_type not in token_types:
        raise ApiError(400, f"Token type must be one of: {token_types}")

    limit = event["queryStringParameters"].get("limit", 10)
    offset = event["queryStringParameters"].get("offset", 0)
    date = event["queryStringParameters"].get("date", "desc")

    return token_type, limit, offset, date


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


def count_organization_tokens(org_id, token_type, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)
    table = create_table(token_type, meta, engine)

    try:
        count_stmt = (
            select([func.count(table.columns.id.distinct())]).
            select_from(table).
            where(table.columns.organization_id == int(org_id))
        )

        connection = engine.connect()
        count_results = connection.execute(count_stmt).fetchall()
        total_records = count_results[0][0]
        connection.close()

        return total_records
    except Exception as e:
        raise ApiError(500, f'Faied to count organization: {e}')


def list_organization_tokens(org_id, token_type, limit, offset, date, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)
    table = create_table(token_type, meta, engine)

    selected_fields = [
        table.columns.id,
        table.columns.organization_id,
        table.columns.token,
        table.columns.expiry_date,
        table.columns.archived,
        table.columns.created_at,
        table.columns.updated_at,
    ]

    try:
        stmt = (
            select(selected_fields).
            where(table.columns.organization_id == int(org_id)).
            limit(limit).
            offset(offset).
            order_by(
                table.columns.created_at.desc() if date == "desc" else table.columns.created_at.asc()
            )
        )

        connection = engine.connect()
        results = connection.execute(stmt).fetchall()
        connection.close()

        records = []
        for r in results:
            tk = {
                "id": r["id"],
                "organization_id": r["organization_id"],
                "token": r["token"],
                "expiry_date": str(datetime.strftime(r["expiry_date"], '%m/%d/%Y %I:%M:%S %p')) if r["expiry_date"] else None,
                "archived": r["archived"],
                "created_at": str(datetime.strftime(r["created_at"], '%m/%d/%Y %I:%M:%S %p')),
                "updated_at": str(datetime.strftime(r["updated_at"], '%m/%d/%Y %I:%M:%S %p')),
            }
            records.append(tk)

        return records
    except Exception as e:
        raise ApiError(500, f'Faied to list organization: {e}')


def lambda_handler(event, context):
    if 'source' in event and event['source'] == 'aws.events':
        return {
            'msg': 'Warm up triggered..............'
        }

    try:
        authorize(event["queryStringParameters"].get("token", ""))

        db_credentials = get_database_secrets()
        org_id = get_organization_id(event)
        token_type, limit, offset, date = parse_query_parameters(event)

        count = None
        tokens = None
        if token_type == 'documentation':
            count = count_organization_tokens(
                org_id, "documentation_tokens", db_credentials)
            tokens = list_organization_tokens(
                org_id, "documentation_tokens", limit, offset, date, db_credentials)
        else:
            count = count_organization_tokens(
                org_id, "referral_tokens", db_credentials)
            tokens = list_organization_tokens(
                org_id, "referral_tokens", limit, offset, date, db_credentials)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "statusCode": 200,
                "total_records": count,
                "records": tokens,
                "token_type": token_type
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
