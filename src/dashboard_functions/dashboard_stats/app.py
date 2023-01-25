import json
import boto3
from sqlalchemy import create_engine, select, MetaData, Table, extract,cast,Date,or_
import datetime
import os


response_headers = {
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET",
                    }
def db_oprations(connection,stmt):

    try:
        results = connection.execute(stmt).fetchall()
        return results

    except Exception as e:
        return {
            "statusCode": 200,
            "headers": response_headers,
                    "body": json.dumps({
                    "msg": "something went wrong",
                    "error_response":e
                    },),
            "isBase64Encoded": False,
        }

def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    token = event["queryStringParameters"].get("token", "") if "queryStringParameters" in event and event["queryStringParameters"] != None else None
    if token:
        lambda_client = boto3.client("lambda")
        response = lambda_client.invoke(
            FunctionName=os.environ["GET_USER_ARN"],
            InvocationType="RequestResponse",
            Payload=json.dumps({"type": "session_token", "token": token}),
        )
        payload = json.load(response["Payload"])
        error = None
        statusCode, error =  (400, "error while accessing token") if "error" in payload else (400, payload["msg"]) if "user_id" not in payload else (200, None)
        if error:
            return {
                    "statusCode": statusCode,
                    "headers": response_headers,
                    "body" : json.dumps({
                        "statusCode": statusCode,
                        "msg": error
                    }),
                    "isBase64Encoded": False,
                }
        user_id = payload["user_id"]
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
                "body": json.dumps({
                        "msg": "error while accessing secrets manager",
                        "error": payload["error"],
                        },
                    ),
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
                'referral_requests',
                metadata,
                autoload=True,
                autoload_with=engine
            )

        failures_stmt = select([
                table.columns.id,
                table.columns.emr_type,
                table.columns.emr_status,
                table.columns.created_at
            ]).where(or_(table.columns.failed_internal == True, table.columns.emr_status == 2, table.columns.emr_status == None), cast(table.columns.created_at, Date)==datetime.datetime.now().date(), table.columns.archived == False)

        success_stmt = select([
                table.columns.id,
                table.columns.emr_type,
                table.columns.emr_status,
                table.columns.created_at,
                cast(table.columns.created_at, Date)
            ]).where(table.columns.failed_internal == False, table.columns.emr_status == 1, cast(table.columns.created_at, Date)==datetime.datetime.now().date(), table.columns.archived == False)

        failures_stmt_by_month = select([
                table.columns.id,
                table.columns.emr_type,
                table.columns.emr_status,
                table.columns.created_at
            ]).where(or_(table.columns.failed_internal == True, table.columns.emr_status == 2, table.columns.emr_status == None), table.columns.archived == False).filter(extract('month', table.columns.created_at) == datetime.datetime.now().month).filter(extract('year', table.columns.created_at) == datetime.datetime.now().year)

        success_stmt_by_month = select([
                table.columns.id,
                table.columns.emr_type,
                table.columns.emr_status,
                table.columns.created_at
            ]).where(table.columns.failed_internal == False, table.columns.emr_status == 1, table.columns.archived == False).filter(extract('month', table.columns.created_at) == datetime.datetime.now().month).filter(extract('year', table.columns.created_at) == datetime.datetime.now().year)

        connection = engine.connect()
        failures_stmt_result= db_oprations(connection,failures_stmt)
        success_stmt_result= db_oprations(connection,success_stmt)
        failures_stmt_by_month_result= db_oprations(connection,failures_stmt_by_month)
        success_stmt_by_month_result= db_oprations(connection,success_stmt_by_month)

        return {
            "statusCode": 200,
            "headers": response_headers,
            "body": json.dumps({
                "msg": "Data fetched",
                "failures_in_day":len(failures_stmt_result),
                "successful_in_day":len(success_stmt_result),
                "failures_in_month":len(failures_stmt_by_month_result),
                "successful_in_month":len(success_stmt_by_month_result)
            }),
            "isBase64Encoded": False,
        }
    else:
        return {
            "statusCode": 400,
            "headers": response_headers,
            "body":json.dumps({
                "statusCode": 400,
                "msg": "Please provide valid token",
            }),
            "isBase64Encoded": False,
        }