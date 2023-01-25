import json
# from xmlrpc.client import Boolean
from sqlalchemy import create_engine, MetaData, Table, select
import boto3
import os

response_headers = {
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS"
}
lambda_client = boto3.client("lambda")

def authenticate(token, resource):
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
                    "msg": "Error while authenticating",
                    "error": error
                }),
                "isBase64Encoded": False,
            }
    else:
        permissions = payload.get("permissions", "")
        is_master = payload.get("is_master", False)
        if resource == "Internal Request" or (is_master or (permissions and "Allowed" in permissions and "view_permissions" in permissions["Allowed"])):
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
    
    resource = event.get("resource", "")
    token = event["queryStringParameters"].get("token","") if "queryStringParameters" in event and event["queryStringParameters"] != None else ""
    if token:
        session = authenticate(token=token, resource = resource)
        first_name = None
        last_name = None
        role = None
        if "user_id" in session:
            user_id = event["queryStringParameters"].get("user_id",None)
            role_id = event["queryStringParameters"].get("role_id",None)
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
                permissions = Table(
                    "permissions",
                    meta,
                    autoload = True,
                    autoload_with = engine
                )
                if user_id:
                    user_permissions = Table(
                        "user_permissions",
                        meta,
                        autoload = True,
                        autoload_with = engine
                    )
                    users = Table(
                        "users",
                        meta,
                        autoload = True,
                        autoload_with = engine
                    )
                    roles = Table(
                        "roles",
                        meta,
                        autoload = True,
                        autoload_with = engine
                    )
                    user_role_join = users.join(roles, users.columns.role_id == roles.columns.id)
                    user_stmt = select([
                        users.columns.id,
                        users.columns.first_name,
                        users.columns.last_name,
                        roles.columns.role
                    ]).select_from(user_role_join).where(users.columns.id == user_id, users.columns.archived == False)
                    try:
                        user_data = connection.execute(user_stmt).fetchone()
                        if user_data:
                            first_name = user_data["first_name"]
                            last_name = user_data["last_name"]
                            role = user_data["role"]
                        else:
                            return {
                            "statusCode" : 400,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 400,
                                "error" : "User not found"
                            }),
                            "isBase64Encoded": False
                        }
                    except:
                        return {
                            "statusCode" : 500,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 500,
                                "error" : "Something went wrong"
                            }),
                            "isBase64Encoded": False
                        }
                    join = user_permissions.join(permissions, user_permissions.columns.permission_id == permissions.columns.id)
                    select_stmt = select([
                        permissions.columns.id,
                        permissions.columns.category,
                        permissions.columns.level,
                        permissions.columns.display_name,
                        permissions.columns.description
                    ]).select_from(join).where(
                        user_permissions.columns.user_id == user_id
                    )
                elif role_id:
                    role_permissions = Table(
                        "default_role_permissions",
                        meta,
                        autoload = True,
                        autoload_with = engine
                    )
                    roles = Table(
                        "roles",
                        meta,
                        autoload = True,
                        autoload_with = engine
                    )
                    role_name = select([
                        roles.columns.role
                    ]).where(roles.columns.id == role_id)
                    try:
                        role_data = connection.execute(role_name).fetchone()
                        if role_data:
                            role = role_data["role"]
                        else:
                            return {
                            "statusCode" : 400,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 400,
                                "error" : "Role not found"
                            }),
                            "isBase64Encoded": False
                        }
                    except:
                        return {
                            "statusCode" : 500,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 500,
                                "error" : "Something went wrong"
                            }),
                            "isBase64Encoded": False
                        }
                    join = role_permissions.join(permissions, role_permissions.columns.permission_id == permissions.columns.id)
                    select_stmt = select([
                        permissions.columns.id,
                        permissions.columns.category,
                        permissions.columns.level,
                        permissions.columns.display_name,
                        permissions.columns.description
                    ]).select_from(join).where(
                        role_permissions.columns.role_id == role_id
                    )
                else:
                    select_stmt = select({
                        permissions.columns.id,
                        permissions.columns.category,
                        permissions.columns.level,
                        permissions.columns.display_name,
                        permissions.columns.description
                    })
                try:
                    results = connection.execute(select_stmt).fetchall()
                except:
                    return {
                        "statusCode" : 500,
                        "headers" : response_headers,
                        "body" : json.dumps({
                            "statusCode" : 500,
                            "error" : "Something went wrong"
                        }),
                        "isBase64Encoded": False
                    }
                categories = {result["category"] for result in results}
                permission_dict = {}
                for category in categories:
                    permission_dict[category] = []
                    for result in results:
                        if result["category"] == category:
                            permission_dict[category].append({
                                "id" : result["id"],
                                "level" : result["level"],
                                "display_name" : result["display_name"],
                                "description" : result["description"]
                            })
                        else:
                            continue
                response = {
                        "statusCode" : 200,
                        "msg" : "Permissions fetched successfully..."
                    }
                if user_id:
                    response["first_name"] = first_name
                    response["last_name"] = last_name
                    response["role"] = role
                elif role_id:
                    response["role"] = role
                response["permissions"] = permission_dict
                return {
                    "statusCode" : 200,
                    "headers" : response_headers,
                    "body" : json.dumps(response),
                    "isBase64Encoded": False
                }
            else:
                return {
                    "statusCode" : 500,
                    "headers" : response_headers,
                    "body" : json.dumps({
                        "statusCode" : 500,
                        "msg": "error while accessing secrets manager",
                        "error": credentials["error"]
                    }),
                    "isBase64Encoded": False
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
