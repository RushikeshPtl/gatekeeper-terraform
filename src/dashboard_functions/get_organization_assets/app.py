import json
from sqlalchemy import create_engine, select, MetaData, Table
import boto3
import os

response_headers = {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET"
                }

def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }

    if "queryStringParameters" in event and event["queryStringParameters"] != None:
        subdomain=event["queryStringParameters"].get("subdomain","")
    else:
        subdomain=""

    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"secret_type": "Database Credentials"}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        return {
            "statusCode": 500,
            "headers": response_headers,
            "body" : json.dumps({
                "statusCode": 500,
                "msg": "error while accessing secrets manager",
                "error": payload["error"]
            }),
            "isBase64Encoded": False,
        }
    else:
        credentials = payload["credentials"]
        engine = create_engine(
            "postgresql+psycopg2://{}:{}@{}/{}".format(
                credentials["username"],
                credentials["password"],
                credentials["host"],
                credentials["db"],
            )
        )

    metadata = MetaData(engine)
    table = Table(
        'organizations',
        metadata,
        autoload=True,
        autoload_with=engine
    )
    stmt = select(table.columns.assets).select_from(table).where(table.columns.subdomain==str(subdomain))
    connection = engine.connect()
    try:
        results = connection.execute(stmt).fetchall()
    except Exception as e:
        return {
                "statusCode": 200,
                "headers": response_headers,
                "body" : json.dumps({
                    "statusCode": 200,
                    "msg": "something went wrong"
                }),
                "isBase64Encoded": False,
            }
    if len(results)==0:
        return {
                "statusCode": 200,
                "headers": response_headers,
                "body" : json.dumps({
                    "statusCode": 200,
                    "msg": "Please enter valide subdomain"
                }),
                "isBase64Encoded": False,
            }
    assets_json=results[0][0]
    if assets_json==None:
        return {
                "statusCode": 200,
                "headers": response_headers,
                "body" : json.dumps({
                    "statusCode": 200,
                    "msg": "Please add assets...",
                }),
                "isBase64Encoded": False,
            }

    return {
            "statusCode": 200,
            "headers": response_headers,
            "body" : json.dumps({
                "statusCode": 200,
                "msg": "Record fetched...",
                "data":assets_json
            }),
            "isBase64Encoded": False,
            }