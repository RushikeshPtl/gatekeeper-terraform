import json
import boto3
import os
import logging
from sqlalchemy import create_engine, MetaData, Table, select, text, func, and_


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
    title = event["queryStringParameters"].get("title", "")
    limit = event["queryStringParameters"].get("limit", 10)
    offset = event["queryStringParameters"].get("offset", 0)
    date = event["queryStringParameters"].get("date", "desc")
    archived = event["queryStringParameters"].get("archived", False)

    return title, limit, offset, date, archived


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


def count_organizations(title, archived, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)
    table = create_table("organizations", meta, engine)

    count_stmt = None
    title = '''
                organizations.title = '{}' AND
            '''.format(title) if title else ""
            
    count_stmt = select([func.count(table.columns.id.distinct())]).select_from(table).where(text(
        """
            {} organizations.archived = {}
        """.format(title, 'false' if not archived else 'true')
    ))

    try:
        connection = engine.connect()
        count_results = connection.execute(count_stmt).fetchall()
        total_records = count_results[0][0]
        connection.close()

        return total_records
    except Exception as e:
        raise ApiError(500, f'Faied to count organization: {e}')


def list_organization(title, limit, offset, date, archived, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)
    organizations = create_table("organizations", meta, engine)
    organization_contacts = create_table("organization_contacts", meta, engine)
    organization_amd_codes = create_table(
        "organization_amd_codes", meta, engine)

    join = organizations.join(organization_contacts, and_(
        organization_contacts.columns.organization_id == organizations.columns.id, organization_contacts.columns.archived == False), isouter=True).join(organization_amd_codes, and_(
            organization_amd_codes.columns.organization_id == organizations.columns.id, organization_amd_codes.columns.archived == False), isouter=True)

    selected_fields = [
        organizations.columns.id,
        organizations.columns.title,
        organizations.columns.abbr,
        organizations.columns.subdomain,
        organizations.columns.archived,
        organizations.columns.created_at,
        organizations.columns.updated_at,
        organization_contacts.columns.contact_person,
        organization_contacts.columns.phone,
        organization_contacts.columns.mobile,
        organization_contacts.columns.email,
        organization_amd_codes.columns.financial_class,
        organization_amd_codes.columns.referral_provider_code,
        organization_amd_codes.columns.default_referral_status,
    ]

    stmt = None
    title = '''
                organizations.title = '{}' AND
            '''.format(title) if title else ""

    stmt = select(selected_fields).select_from(join).where(text(
        """
           {} organizations.archived = {}
        """.format(title, 'false' if not archived else 'true')
    )).limit(limit).offset(offset).order_by(
        organizations.columns.created_at.desc() if date == "desc" else organizations.columns.created_at.asc())

    try:
        connection = engine.connect()
        results = connection.execute(stmt).fetchall()
        connection.close()

        records = []
        for r in results:
            org = {
                "id": r["id"],
                "title": r["title"],
                "abbr": r["abbr"],
                "subdomain": r["subdomain"],
                "archived": r["archived"],
                "created_at": r["created_at"].isoformat(),
                "updated_at": r["updated_at"].isoformat(),
                "contact_person": r["contact_person"],
                "phone": r["phone"],
                "mobile": r["mobile"],
                "email": r["email"],
                "financial_class": r["financial_class"],
                "referral_provider_code": r["referral_provider_code"],
                "default_referral_status": r["default_referral_status"]
            }
            records.append(org)

        return records
    except Exception as e:
        raise ApiError(500, f'Faied to list organization: {e}')


def lambda_handler(event, context):
    if 'source' in event and event['source'] == 'aws.events':
        return {
            'msg': 'Warm up triggered..............'
        }

    try:
        token = event["queryStringParameters"].get("token", "")
        authorize(token)

        db_credentials = get_database_secrets()

        title, limit, offset, date, archived = parse_query_parameters(event)
        count = count_organizations(title, archived, db_credentials)
        organizations = list_organization(
            title, limit, offset, date, archived, db_credentials)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "statusCode": 200,
                "total_records": count,
                "records": organizations
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