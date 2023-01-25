from sqlalchemy import create_engine, select, MetaData, Table, select,text
import json
import boto3
import os

response_headers = {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
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
        permissions = payload.get("permissions", "")
        is_master = payload.get("is_master", False)
        role_level = 0 if is_master else payload["role_level"] if "role_level" in payload and payload["role_level"] else 10
        if role_level >= 0:
            return {
                "user_id" : payload["user_id"],
                "role_level" : role_level
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
    response_headers = {
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "GET",
                    }
    token = event["queryStringParameters"].get("token", "") if "queryStringParameters" in event and event["queryStringParameters"] != None else None
    if token:
        session = authenticate(token)
        if "user_id" in session:
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

                connection = engine.connect()
                metadata = MetaData(engine)

                roles_table = Table(
                        'roles',
                        metadata,
                        autoload=True,
                        autoload_with=engine
                    )

                roles_stmt = select([
                    roles_table.columns.id,
                    roles_table.columns.role
                ]).where(
                    roles_table.columns.role_level > session["role_level"]
                )
                try:
                    roles = connection.execute(roles_stmt).fetchall()
                except Exception as e:
                    return{
                        "statusCode" : 500,
                        "headers": response_headers,
                            "body":json.dumps({
                                "statusCode": 200,
                                "msg": "Something went wrong",
                                "error_response":e
                            }),
                            "isBase64Encoded": False,
                        }
                if len(roles) != 0:
                    roles_list = []
                    for role in roles:
                        roles_list.append({
                                "id": role["id"],
                                "role": role["role"]
                            })
                    return {
                        "statusCode" : 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "Roles fetched",
                            "roles": roles_list
                        }),
                        "isBase64Encoded": False,
                    }
                else:
                    {
                        "statusCode" : 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "Roles not found",
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


