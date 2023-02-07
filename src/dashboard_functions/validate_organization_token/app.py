import json
import boto3
import os
import logging
from sqlalchemy import create_engine, MetaData, Table, text, select
from datetime import datetime
import pytz


logger = logging.getLogger()
logger.setLevel(logging.INFO)

response_headers = {
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
}

def is_json(json_data):
    try:
        if not isinstance(json_data, dict):
            json.loads(json_data)
        else:
            return True
    except ValueError:
        return False
    return True


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


def get_token(event):
    if not event["queryStringParameters"] or not event["queryStringParameters"]["token"]:
        raise ApiError(400, f"Token is required")
    return event["queryStringParameters"].get("token")

def getOrgIdentifier(event):
    params = event.get("queryStringParameters", None)
    if params:
        if "org_abbr" in params and params["org_abbr"]:
            field = 'abbr'
            value = event["queryStringParameters"]["org_abbr"]
        elif "subdomain" in params and params["subdomain"]:
            field = 'subdomain'
            value = event["queryStringParameters"]["subdomain"]
        else:
            raise ApiError(400, f"Invalid Parameters")
        return field, value
    else:
        raise ApiError(400, f"Invalid Parameters")

def create_table(name, meta, engine):
    tb = Table(
        name,
        meta,
        autoload=True,
        autoload_with=engine
    )

    return tb


def get_db_token(token, token_type, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)
    table = create_table(token_type, meta, engine)

    try:
        stmt = (
            select([
                table.columns.id,
                table.columns.token,
                table.columns.expiry_date,
                table.columns.archived,
                table.columns.organization_id
            ]).
            select_from(table).
            where(table.columns.token == token)
        )

        connection = engine.connect()
        result = connection.execute(stmt).fetchone()
        connection.close()

        if not result:
            return {}
        else:
            return {
                "id": result['id'],
                "token": result['token'],
                "expiry_date": result['expiry_date'],
                "archived": result['archived'],
                "organization_id": result['organization_id'],
            }

    except Exception as e:
        raise ApiError(
            500, f'Faied to fetch organization token {token_type}: {e}')


def get_organization_by_subdomain(subdomain, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)
    table = create_table("organizations", meta, engine)

    try:
        stmt = (
            select([
                table.columns.id,
                table.columns.subdomain,
                table.columns.archived,
            ]).
            select_from(table).
            where(table.columns.subdomain == str(subdomain))
        )

        connection = engine.connect()
        result = connection.execute(stmt).fetchone()
        connection.close()

        if not result:
            return {}
        else:
            return {
                "id": result['id'],
                "subdomain": result['subdomain'],
                "archived": result['archived'],
            }

    except Exception as e:
        raise ApiError(
            500, f'Faied to fetch organization hash subdomain {subdomain}: {e}')

def get_organization_token(field, value, tk_type, token, db_credentials):
   
    engine, meta   = create_db_engine_and_meta(db_credentials)
    table          = create_table("organizations", meta, engine)
    token_table    = create_table(tk_type, meta, engine)

    try:
        
        join = table.join(token_table, table.columns.id == token_table.columns.organization_id)
        select_stmt = select([
                token_table.columns.id,
                token_table.columns.organization_id,
                token_table.columns.archived,
                token_table.columns.expiry_date,
            ]).select_from(join).where(text(
                    '''
                        ({}  = '{}')
                    '''.format(field, value)
                ),
                token_table.columns.token == token, 
                token_table.columns.archived == False, table.columns.archived == False
            )
            
        connection = engine.connect()
        result = connection.execute(select_stmt).fetchone()
        connection.close()
        
        
           
        if not result:
            return {}
        else:
            return {
                "id": result['id'],
                "organization_id": result['organization_id'],
                "expiry_date": result['expiry_date'],
                "archived": result['archived'],
            }

    except Exception as e:
        raise ApiError(
            500, f'Faied to fetch organization: {e}')



def parse_query_parameters(event):
    token_type = event["queryStringParameters"].get("token_type", "")
    token = event["queryStringParameters"].get("token", "")
    if not token_type:
        raise ApiError(400, f"Token type is required")

    token_types = ['documentation', 'referral']
    if token_type not in token_types:
        raise ApiError(400, f"Token type must be one of: {token_types}")
    if not token:
        raise ApiError(400, "Token Required")
    return token_type, token


def lambda_handler(event, context):
   
    if is_json(event):
        if not isinstance(event, dict):
            event = json.loads(event)
        if "source" in event and event["source"] == "aws.events":
            print("Warm up triggered..............")
            return {
                "msg" : "Warm up triggered.............."
            }
        resource = event.get("resource", "")
        print("Resource ----------------------> ", resource)

        try:
           
            token_type, token = parse_query_parameters(event)
            db_credentials = get_database_secrets()
            field, value   = getOrgIdentifier(event)
            tk_type        = "documentation_tokens" if token_type == "documentation" else "referral_tokens"
            
            db_organization = get_organization_token(field, value, tk_type, token, db_credentials)
            
            
            if db_organization:
                org_id       = db_organization['organization_id']
                archived     = db_organization['archived']
                expiry_date  = db_organization['expiry_date']
                expiry_date  = expiry_date.replace(tzinfo=pytz.utc) if expiry_date else None
                present      = datetime.now()
                present      = present.replace(tzinfo=pytz.utc)
               
                if archived or (expiry_date and expiry_date < present):
                    raise ApiError(400, 'Invalid token')

                return {
                    "statusCode": 200,
                    "body": json.dumps({
                        "statusCode": 200,
                        "org_id": org_id,
                        "token_type": token_type,
                        "msg": "Token valid"
                    }),
                    "headers": response_headers,
                }
            else:
                raise ApiError(400, "Organization not found")
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