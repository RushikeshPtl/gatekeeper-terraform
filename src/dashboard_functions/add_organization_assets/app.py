import json
from sqlalchemy import create_engine, select, MetaData, Table, text,update
import boto3
from botocore.exceptions import ClientError
import os
import base64
import datetime

def convertBaseToImage(file):
    fi = file.replace("data:image/svg+xml;base64,", "")
    decodeit = open('/tmp/hello_level1.svg', 'wb')
    decodeit.write(base64.b64decode(fi))
    decodeit.close()

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
        role_level = payload.get("role_level", 10)
        if is_master or (permissions and "Allowed" in permissions and ("view_equal_user" in permissions["Allowed"] or "view_lower_user" in permissions["Allowed"])):
            if not is_master and "view_equal_user" in permissions["Allowed"]:
                role_level -= 1
            elif is_master:
                role_level = 0
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

def is_json(json_data):
    try:
        if not isinstance(json_data, dict):
            json.loads(json_data)
        else:
            return True
    except ValueError:
        return False
    return True

def lambda_handler(event, context):
    response_headers = {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
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
        token = event.get("token", None)

        if token:
            session = authenticate(token)
            if "user_id" in session:
                organization_id = event.get("organization_id", None)
                file = event.get("file", None)
                primary_color =event.get("primary_color", None)
                secondary_color = event.get("secondary_color", None)
                token = event.get("token", None)

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

                    s3_client = boto3.client('s3')
                    bucket = os.environ["STAGE_S3_BUCKET"] if os.environ["ENVIRONMENT"] == "dev" else os.environ["PROD_S3_BUCKET"]

                    if file:
                        logo=convertBaseToImage(file)
                        body='/tmp/hello_level1.svg'
                        Key="System/Organizations/{}/logo.svg".format(organization_id)
                        today = datetime.datetime.now()
                        expiry_time = today + datetime.timedelta(hours=24)
                        ALLOWED_UPLOAD_ARGS ={"Expires":expiry_time,"ContentType":"image/svg+xml"}
                        try:
                            response = s3_client.upload_file(
                                    body,
                                    bucket,
                                    Key,
                                    ALLOWED_UPLOAD_ARGS
                                    )
                        except ClientError as e:
                            return  {
                                    "statusCode": 200,
                                    "headers": response_headers,
                                    "body" : json.dumps({
                                        "statusCode": 200,
                                        "msg": "Something went wrong with s3 " + e
                                    }),
                                    "isBase64Encoded": False,
                                }

                    metadata = MetaData(engine)
                    table = Table(
                        'organizations',
                        metadata,
                        autoload=True,
                        autoload_with=engine
                    )
                    stmt = select(table.columns.assets).select_from(table).where(text(
                                """
                                    organizations.id = {}
                                """.format(organization_id)
                    ))
                    connection = engine.connect()
                    try:
                        results = connection.execute(stmt).fetchall()
                    except Exception as e:
                        return {
                            "statusCode": 200,
                            "headers": response_headers,
                            "body" : json.dumps({
                                "statusCode": 200,
                                "msg": "please provide valid organization id..."
                            }),
                            "isBase64Encoded": False,
                        }
                    asset_json=results[0][0] if results[0][0] != None else {"logo":{"key":""},"color_scheme":{"primary_color":"","secondary_color":""}}
                    if primary_color:
                        asset_json["color_scheme"]["primary_color"]=primary_color
                    if secondary_color:
                        asset_json["color_scheme"]["secondary_color"]=secondary_color
                    if file:
                        asset_json["logo"]["key"]=Key
                    connection = engine.connect()
                    add_json =(
                        update(table)
                        .where(table.columns.id == int(organization_id))
                        .values(
                            assets = asset_json
                        )
                    )

                    try:
                        result = connection.execute(add_json)
                    except:
                        return {
                                "statusCode" : 500,
                                "headers" : response_headers,
                                "body" : json.dump({
                                    "statusCode" : 500,
                                    "msg" : "Something went wrong"
                                }),
                                "isBase64Encoded": False,
                            }

                    return {
                            "statusCode" : 200,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 200,
                                "msg" : "Assets added successfully..."
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