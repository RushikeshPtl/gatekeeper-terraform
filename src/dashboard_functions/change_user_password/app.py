from sqlalchemy import select
from sqlalchemy import create_engine, select, MetaData, Table, text,update
import json
import bcrypt
import boto3
import os

response_headers = {
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS"
}
lambda_client = boto3.client("lambda")

def is_json(json_data):
    try:
        if not isinstance(json_data, dict):
            json.loads(json_data)
        else:
            return True
    except ValueError:
        return False
    return True

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
        return {"user_id" : payload["user_id"]}

def update_password(table,connection,user_id,new_password,response_headers):
    bytes = new_password.encode('utf-8')
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(bytes, salt)

    update_stmt = (
                    update(table)
                    .where(table.columns.id == user_id)
                    .values(
                            password = str(hash, 'UTF-8'),
                            password_reset_token = None
                        )
                       )
    connection.execute(update_stmt)

    return {
           "statusCode": 200,
           "headers": response_headers,
            "body":json.dumps({
                        "statusCode": 200,
                        "msg": "Password changed successfully...",
                    }),
            "isBase64Encoded": False,
            }

def lambda_handler(event, context):
    response_headers = {
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "POST",
                    }

    if is_json(event):
        if not isinstance(event, dict):
            event = json.loads(event)
        if "source" in event and event["source"] == "aws.events":
            print("Warm up triggered..............")
            return {
                "msg" : "Warm up triggered.............."
            }
        event = json.loads(event["body"])
        client = boto3.client("lambda")
        response = client.invoke(
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
                    "msg": "error while accessing secrets manager"
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

            flag=event.get("flag","")
            token=event.get("token","")
            old_password=event.get("old_password","")
            new_password=event.get("new_password","")
            password_reset_token=event.get("password_reset_token","")

            if len(new_password) < 8 or len(new_password) > 16:
                return {
                        "statusCode": 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "Password length must be 8 to 16 characters",
                            }),
                            "isBase64Encoded": False,
                        }

            if flag=="change_password":
                if token:
                    session = authenticate(token)
                    if "user_id" in session:
                        user_id = session["user_id"]
                        stmt = select([
                                table.columns.id,
                                table.columns.password,
                            ]).where(text(
                                '''
                                    (id  = '{}')
                                '''.format(user_id)))

                        connection = engine.connect()
                        try:
                            results = connection.execute(stmt).fetchall()
                        except Exception as e:
                            return {
                                "statusCode": 200,
                                "headers": response_headers,
                                "body":json.dumps({
                                    "statusCode": 200,
                                    "msg": "something went wrong",
                                    "error_response":e
                                }),
                                "isBase64Encoded": False,
                            }


                        db_pass=results[0]["password"]
                        bytepass=bytes(db_pass, 'utf-8')
                        userBytes = old_password.encode('utf-8')
                        result = bcrypt.checkpw(userBytes, bytepass)

                        if result==False:
                            return {
                                "statusCode": 200,
                                "headers": response_headers,
                                "body":json.dumps({
                                    "statusCode": 200,
                                    "msg": "Please check password...",
                                }),
                                "isBase64Encoded": False,
                            }

                        elif result==True:
                            update_response = update_password(table,connection,user_id,new_password,response_headers)
                            return update_response
                    else:
                        return session
                else:
                    return {
                        "statusCode": 400,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 400,
                            "msg": "Please send valid token...",
                        }),
                        "isBase64Encoded": False,
                    }
            elif flag =="forgot_password":
                stmt = select([
                        table.columns.id,
                        table.columns.password,
                ]).where(text(
                   '''
                      (password_reset_token  = '{}')
                      AND (archived = 'False')
                   '''.format(password_reset_token)))
                try:
                    results = connection.execute(stmt).fetchall()
                except Exception as e:
                    return {
                        "statusCode": 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "something went wrong...",
                        }),
                        "isBase64Encoded": False,
                    }

                if len(results)==0:
                    return {
                        "statusCode": 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "Please send valid token...",
                        }),
                        "isBase64Encoded": False,
                    }

                user_id=results[0]["id"]
                update_response = update_password(table,connection,user_id,new_password,response_headers)
                return update_response
            else:
                return {
                        "statusCode": 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "Please send valid flag...",
                        }),
                        "isBase64Encoded": False,
                    }

    else:
        response = {
            "statusCode": 400,
            "headers": response_headers,
            "body": json.dumps({
                "msg": "Failed with issues: Invalid JSON input.",
                "statusCode": 200
            }),
            "isBase64Encoded": False,
        }
        return response