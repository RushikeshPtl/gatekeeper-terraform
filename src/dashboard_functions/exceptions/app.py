import json
# from xmlrpc.client import Boolean
from sqlalchemy import create_engine, MetaData, Table
import boto3
import os

response_headers = {
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS"
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

def create_table(name):
    tb = Table(
        name,
        meta,
        autoload=True,
        autoload_with=engine
    )

    return tb

def get_http_method(event):
    return event.get("httpMethod")

# def get_token(event):
#     if not event["queryStringParameters"] or not event["queryStringParameters"].get("token"):
#         raise ApiError(401, 'Unauthorized user')
#     return event["queryStringParameters"].get("token")

def addLogEntry(data):
    log = create_table("error_logs")

    try:
        add_log = log.insert().values(
            url             = data["url"],
            payload         = data["payload"],
            error_type      = data["error_type"],
            error_details   = data["error_details"],
            error_reason    = data["error_reason"]
        )

        connection = engine.connect()
        result = connection.execute(add_log)
        connection.close()

        log_id = result.inserted_primary_key[0]
        return log_id
    except Exception as e:
        raise ApiError(500, f'Faied to log error entry: {e}')

def logExceptionError(event):
    try:
        body = json.loads(event['body'])
        log_id = addLogEntry(body)

        return {
            "statusCode": 200,
            "body": json.dumps({
                 "statusCode": 200,
                 "msg": "Data logged successfully!",
                 "log_id": log_id
            }),
            "headers": response_headers,
        }
    except ApiError as e:
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
            return logExceptionError(event)
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
