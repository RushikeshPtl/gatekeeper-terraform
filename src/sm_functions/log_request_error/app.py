import json
import boto3
from sqlalchemy import create_engine, MetaData, Table, select, update, text, bindparam
import os

lambda_client = boto3.client("lambda")

def get_credentials():
    '''
        Invokes the GetSecrets functions to fetch database credentials
    '''
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"secret_type": "Database Credentials"}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        return payload
    else:
        credentials = payload["credentials"]
        return credentials

def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    request_id = event.get("request_id", None)
    error_type = event.get("error_type", "")
    error_details = event.get("error_details", "")
    error_details = json.dumps(error_details) if isinstance(error_details, dict) else error_details
    error_reason = event.get("error_reason", "")
    payload = event.get("payload", {})
    url = event.get("url", "")
    credentials = get_credentials()
    if not "error" in credentials:
        engine = create_engine(
            "postgresql+psycopg2://{}:{}@{}/{}".format(
                credentials["username"],
                credentials["password"],
                credentials["host"],
                credentials["db"],
            )
        )
        meta = MetaData(engine)
        connection = engine.connect()
        request_error_details = Table(
            "request_error_details",
            meta,
            autoload = True,
            autoload_with = engine
        )
        if request_id:
            existing_error_stmt = select([
                request_error_details.columns.id
            ]).where(request_error_details.columns.request_id == int(request_id),
                    request_error_details.columns.archived == False)
            try:
                results = connection.execute(existing_error_stmt).fetchall()
                existing_error_ids = [result["id"] for result in results]
                params = []
                for id in existing_error_ids:
                    params.append({"archived" : True, "_id" : id})
                if params:
                    archive_stmt = (
                                    update(request_error_details)
                                    .where(request_error_details.columns.id == bindparam("_id"))
                                    .values(
                                        archived = bindparam("archived")
                                    )
                                )
                    try:
                        res = connection.execute(archive_stmt, params)
                    except:
                        response = {
                            "statusCode" : 500,
                            "msg" : "Something Went Wrong"
                        }
                        return response
            except:
                response = {
                    "statusCode" : 500,
                    "msg" : "Something Went Wrong"
                }
                return response
        inset_error_details = request_error_details.insert().values(
            request_id = request_id,
            error_type = error_type,
            error_details = error_details,
            error_reason = error_reason,
            url = url,
            payload = payload
        )
        try:
            result = connection.execute(inset_error_details)
            request_error_id = result.inserted_primary_key[0]
            statusCode = 200
            response = {
                "statusCode" : 200,
                "msg" : "Error log created successfully",
                "request_error_id" : request_error_id
            }
        except:
            response = {
                "statusCode" : 500,
                "msg" : "Something Went Wrong",
            }
        return response
    else:
        return {
            "statusCode" : 500,
            "msg": "error while accessing secrets manager",
            "error": credentials["error"]
        }