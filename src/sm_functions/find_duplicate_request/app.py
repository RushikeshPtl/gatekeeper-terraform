import json
from sqlalchemy import create_engine, MetaData, Table, select, update, func, text
from sqlalchemy.sql import func
import boto3
import psycopg2
from botocore.exceptions import ClientError
import os

def escape_apostrophe(string):
    items = string.split("'")
    new_string = items[0]
    for i in items[1:]:
        new_string += "''" + i
    return new_string

def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    if event["request_id"]:
        return {
                "status_code": 200,
                "msg": "Update Request",
                "referral_request_id": event["request_id"],
                "validation_checks" : event["validation_checks"],
                "original_request" : event["original_request"],
                "generic_json" : event["generic_json"]
            }
    client = boto3.client("lambda")
    response = client.invoke(
        FunctionName = os.environ["GET_SECRET_ARN"],
        InvocationType = "RequestResponse",
        Payload = json.dumps({"secret_type": "Database Credentials"})
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        return {
            "error_code": 500,
            "msg": "error while accessing secrets manager",
            "error": payload["error"]
        }
    else:
        try:
            generic_json = event["generic_json"]
            client_firstname = escape_apostrophe(generic_json["client"]["firstname"]) if generic_json["client"]["firstname"] else ""
            client_lastname = escape_apostrophe(generic_json["client"]["lastname"]) if generic_json["client"]["lastname"] else ""
            client_dob = generic_json["client"]["dob"]
            credentials = payload["credentials"]
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
            generic_json = event["generic_json"]
            referral_requests = Table(
                "referral_requests",
                meta,
                autoload=True,
                autoload_with=engine
            )

            stmt = select([
                referral_requests.columns.id,
            ]).where(text(
                            '''
                                internal_request -> 'client' ->> 'firstname' = '{}'
                                AND internal_request -> 'client' ->> 'lastname' = '{}'
                                AND internal_request -> 'client' ->> 'dob' = '{}'
                                AND archived = false
                            '''.format(client_firstname, client_lastname, client_dob)
                        ))
            results = connection.execute(stmt).fetchall()
            if results:
                connection.close()
                return {
                    "status_code": 200,
                    "msg": "Duplicate Request Found",
                    "duplicate_request_ids": [result[0] for result in results],
                    "validation_checks" : event["validation_checks"],
                    "original_request" : event["original_request"],
                    "generic_json" : generic_json
                }
            else:
                connection.close()
                return {
                    "status_code": 200,
                    "msg": "Duplicate Not Found",
                    "validation_checks" : event["validation_checks"],
                    "original_request" : event["original_request"],
                    "generic_json" : generic_json
                }
        except Exception as e:
            return {
                    "request_id": event.get("request_id", None),
                    "payload": event.get("generic_json", {}),
                    "is_validate": "failed",
                    "error_reason": "Error while finding duplicate request [PATH: /functions/find_duplicate_request]",
                    "error_exception": str(e),
                    "msg": "Log Error",
                }

