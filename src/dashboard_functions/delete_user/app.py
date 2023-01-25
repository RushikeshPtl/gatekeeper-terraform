from sqlalchemy import create_engine, MetaData, Table, update, select
import json
import boto3
import os

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
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    user_id=event["queryStringParameters"].get("user_id","") if "queryStringParameters" in event and event["queryStringParameters"] != None else ""
    token = event["queryStringParameters"].get("token","") if "queryStringParameters" in event else ""
    if token: 
        session = authenticate(token)
        if "user_id" in session:
            if user_id == "":
                return {
                        "statusCode": 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "Please provide valid user id",
                        }),
                        "isBase64Encoded": False,
                    }
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

                connection = engine.connect()
                metadata = MetaData(engine)

                table = Table(
                        'users',
                        metadata,
                        autoload=True,
                        autoload_with=engine
                    )
                connection = engine.connect()
                select_stmt = select(
                    table.columns.id
                ).where(
                    table.columns.id == user_id,
                    table.columns.archived == False
                )
                users = connection.execute(select_stmt).fetchall()
                if users:
                    update_stmt = (
                                    update(table)
                                    .where(table.columns.id == user_id)
                                    .values(
                                        archived = 1
                                    )
                                )

                    try:
                        results=connection.execute(update_stmt)
                    except Exception as e:
                        return {
                                "statusCode": 500,
                                "headers": response_headers,
                                "body":json.dumps({
                                    "statusCode": 500,
                                    "msg": "something went wrong",
                                    "error_response":e
                                }),
                                "isBase64Encoded": False,
                                }
                    return {
                            "statusCode": 200,
                            "headers": response_headers,
                            "body":json.dumps({
                                "statusCode": 200,
                                "msg": "User deleted successfully",
                            }),
                            "isBase64Encoded": False,
                        }
                else:
                    return {
                                "statusCode": 200,
                                "headers": response_headers,
                                "body":json.dumps({
                                    "statusCode": 200,
                                    "msg": "User Not Found",
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