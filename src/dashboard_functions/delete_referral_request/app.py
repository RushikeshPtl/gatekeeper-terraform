import json
from sqlalchemy import create_engine, MetaData, Table,update
import os
import boto3

response_headers = {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "OPTIONS, DELETE"
                }
lambda_client = boto3.client("lambda")

def authenticate(token):
    '''
        Invokes the GetSessionUser to verify the session token & fetch user_id

        Input:
            - token(REQUIRED) : String
        Output:
            - dict
    '''
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
    else:
        is_master = payload.get("is_master", False)
        if is_master:
            return {
                "user_id" : payload["user_id"],
            }
        else:
            return {
                "statusCode": 400,
                "headers": response_headers,
                "body":json.dumps({
                    "statusCode": 400,
                    "msg": "Unauthorized user",
                }),
                "isBase64Encoded": False,
            }

def lambda_handler(event, context):
    """
        Function Name : DeleteDataFromDatabase

        - This function will delete the data from database.

        Response:
        -----

    """
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }

    token = event["queryStringParameters"].get("token","") if "queryStringParameters" in event else ""
    if token:
        session = authenticate(token)
        if "user_id" in session:
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
            "referral_requests",
            metadata,
            autoload=True,
            autoload_with=engine
            )
            stmt=(
                update(table).
                where(table.columns.id == event["pathParameters"]["id"]).
                values(archived=1)
            )
            connection = engine.connect()
            try:
                results = connection.execute(stmt)
                return {
                    "statusCode": 200,
                    "headers": response_headers,
                    "body": json.dumps({
                        "statusCode": 200,
                        "msg": "record deleted",
                    }),
                    "isBase64Encoded": False,
                }
            except Exception as e:
                return {
                    "statusCode": 200,
                    "headers": response_headers,
                    "body": json.dumps({
                        "statusCode": 200,
                        "msg": "Somthing went wrong.",
                        "error_response":e
                    }),
                    "isBase64Encoded": False,
                }
        else:
            return session
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