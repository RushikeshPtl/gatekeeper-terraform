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

def get_tokens_bucket():
    s3_client = boto3.client("s3")
    bucket = os.environ["STAGE_BUCKET_NAME"] if os.environ["ENVIRONMENT"] == "dev" else os.environ["PROD_BUCKET_NAME"]

    return s3_client, bucket

def authorize(form_validator):

    try:
        s3_client, bucket = get_tokens_bucket()
        s3_key            = "form_validator.json"
        response          = s3_client.get_object(
                                Bucket=bucket,
                                Key=s3_key
                            )
        token_data = json.load(response["Body"])
        token      = token_data.get("token", "")
       
    except:
         raise ApiError(
            500, f"error while accessing token from s3")

    if token == form_validator:
            return token
    else:
        raise ApiError(400, f"Invalid Token")
        

def parse_query_parameters(event):
    
    if event["queryStringParameters"] and event["queryStringParameters"].get("subdomain", ""):
        subdomain = event["queryStringParameters"].get("subdomain", "")
    else:
        raise ApiError(400, f"Invalid subdomain")

    if event["queryStringParameters"] and event["queryStringParameters"].get("form_validator", ""):
        form_validator = event["queryStringParameters"].get("form_validator", "")
    else:
        raise ApiError(400, f"Invalid Token Parameters")    

    return form_validator, subdomain


def get_database_secrets():
    lambda_client = boto3.client('lambda')
    response = lambda_client.invoke(
        FunctionName   = os.environ['GET_SECRET_ARN'],
        InvocationType = 'RequestResponse',
        Payload        = json.dumps({'secret_type': 'Database Credentials'}),
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


def get_organization_token(subdomain, token_type, db_credentials):
    engine, meta = create_db_engine_and_meta(db_credentials)
    token_table  = create_table(token_type, meta, engine)
    table        = create_table("organizations", meta, engine)
    data         = []

    try:
       
        join = table.join(token_table, table.columns.id == token_table.columns.organization_id)
        select_stmt = select([
                token_table.columns.token
            ]).select_from(join).where( 
                table.columns.abbr == subdomain, token_table.columns.archived == False, table.columns.archived == False
            )
        
        connection = engine.connect()
        results    = connection.execute(select_stmt).fetchone()
        connection.close()
       
    except Exception as e:
        raise ApiError(500, f'Faied to fetch referral token: {e}')
    
    if results:

        token = results["token"] if results["token"] else ""
        if token:
         
            data = {
                "token": token,
                "subdomain": subdomain
            }
        else:
            raise ApiError(500, f'Token not found for subdomain')
        return data
    else:
        raise ApiError(500, f'Token not found for subdomain')


def lambda_handler(event, context):
    if 'source' in event and event['source'] == 'aws.events':
        return {
            'msg': 'Warm up triggered..............'
        }

    try:

        form_validator, subdomain = parse_query_parameters(event)

        #validate token with s3 token
        authorize(form_validator)

        #get token data of subdomain
        db_credentials = get_database_secrets()
        token          = None
        token          = get_organization_token(subdomain, "referral_tokens", db_credentials)
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "statusCode": 200,
                "data": token
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
