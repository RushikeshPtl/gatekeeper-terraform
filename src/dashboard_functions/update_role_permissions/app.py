import json
# from xmlrpc.client import Boolean
from sqlalchemy import create_engine, MetaData, Table, select
import boto3
import os
from sqlalchemy.exc import IntegrityError

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
        is_master = payload.get("is_master", False)
        permissions = payload.get("permissions", "")
        if is_master or ("Allowed" in permissions and "edit_role_permissions" in permissions["Allowed"]):
            return {
                "user_id" : payload["user_id"]
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
    if is_json(event):
        if not isinstance(event, dict):
            event = json.loads(event)
        if "source" in event and event["source"] == "aws.events":
            print("Warm up triggered..............")
            return {
                "msg" : "Warm up triggered.............."
            }
        event = json.loads(event["body"])
        token = event.get("token", "")
        if token:
            session = authenticate(token=token)
            if "user_id" in session:
                role_id = event["role_id"]
                apply_all = event.get("apply_all", False)
                add_permissions = event.get("add_permissions", [])
                remove_permissions = event.get("remove_permissions", [])
                if role_id:
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
                        role_permissions = Table(
                            "default_role_permissions",
                            meta,
                            autoload = True,
                            autoload_with = engine
                        )
                        add_permission_list = []
                        if add_permissions:
                            select_permissions = select(
                                    role_permissions.columns.permission_id
                                ).where(role_permissions.columns.role_id == role_id)
                            try:
                                existing_permissions = [permission["permission_id"] for permission in connection.execute(select_permissions).fetchall()]
                            except:
                                return {
                                        "statusCode" : 500,
                                        "headers" : response_headers,
                                        "body" : json.dumps({
                                            "statusCode" : 500,
                                            "msg": "Something went wrong while fetching existing permissions",
                                        }),
                                        "isBase64Encoded": False,
                                    }
                            for permission in add_permissions:
                                permission_id = permission["id"]
                                if permission_id not in existing_permissions:
                                    assign_permission = role_permissions.insert().values(
                                        role_id = role_id,
                                        permission_id = permission_id
                                    )
                                    try:
                                        result = connection.execute(assign_permission)
                                        existing_permissions.append(permission_id)
                                        add_permission_list.append({"id" : permission_id, "display_name" : permission["display_name"]})
                                    except:
                                        return {
                                                "statusCode" : 500,
                                                "headers" : response_headers,
                                                "body" : json.dumps({
                                                    "statusCode" : 500,
                                                    "msg": "Something went wrong",
                                                }),
                                                "isBase64Encoded": False,
                                            }
                        remove_permission_list = []
                        if remove_permissions:
                            for permission in remove_permissions:
                                permission_id = permission["id"]
                                remove_permission = role_permissions.delete().where(
                                    role_permissions.columns.role_id == role_id,
                                    role_permissions.columns.permission_id == permission_id
                                )
                                try:
                                    result = connection.execute(remove_permission)
                                    remove_permission_list.append({"id" : permission_id, "display_name" : permission["display_name"]})
                                except:
                                    return {
                                            "statusCode" : 500,
                                            "headers" : response_headers,
                                            "body" : json.dumps({
                                                "statusCode" : 500,
                                                "msg": "Something went wrong",
                                            }),
                                            "isBase64Encoded": False,
                                        }
                        if add_permission_list or remove_permission_list:
                            update_json = lambda_client.invoke(
                                FunctionName=os.environ["UPDATE_PERMISSION_JSON_ARN"],
                                InvocationType="Event",
                                Payload=json.dumps({
                                    "type" : "role_permissions",
                                    "role_id" : role_id,
                                    "add_permissions" : add_permission_list,
                                    "remove_permissions" : remove_permission_list
                                    }
                                ),
                            )
                            if apply_all:
                                users = Table(
                                    "users",
                                    meta,
                                    autoload = True,
                                    autoload_with = engine
                                )
                                select_users = select([
                                    users.columns.id
                                ]).where(
                                    users.columns.role_id == role_id,
                                    users.columns.archived == False
                                )
                                try:
                                    users = connection.execute(select_users).fetchall()
                                except:
                                    return {
                                        "statusCode" : 500,
                                        "headers" : response_headers,
                                        "body" : json.dumps({
                                            "statusCode" : 500,
                                            "msg": "Something went wrong",
                                        }),
                                        "isBase64Encoded": False,
                                    }
                                user_ids = [user["id"] for user in users]
                                add_permissions = lambda_client.invoke(
                                    FunctionName=os.environ["UPDATE_USER_PERMISSION_ARN"],
                                    InvocationType="Event",
                                    Payload=json.dumps({
                                        "resource" : "Internal Request",
                                        "user_ids" : user_ids,
                                        "add_permissions" : add_permission_list,
                                        "remove_permissions" : remove_permission_list,
                                        "token" : token
                                        }
                                    ),
                                )
                            return {
                                "statusCode" : 200,
                                "headers" : response_headers,
                                "body" : json.dumps({
                                    "statusCode" : 200,
                                    "msg": "Permissions updated successfully...",
                                }),
                                "isBase64Encoded": False,
                            }
                        else:
                            return {
                                "statusCode" : 200,
                                "headers" : response_headers,
                                "body" : json.dumps({
                                    "statusCode" : 200,
                                    "msg": "No permissions provided...",
                                }),
                                "isBase64Encoded": False,
                            }

                    else:
                        return {
                            "statusCode" : 500,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 500,
                                "msg": "error while accessing secrets manager",
                                "error": credentials["error"],
                            }),
                            "isBase64Encoded": False,
                        }
                else:
                    return {
                            "statusCode" : 400,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "statusCode" : 400,
                                "msg": "Role ID Required"
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
    else:
        response = {
            "statusCode": 400,
            "headers": response_headers,
            "body": json.dumps({
                "msg": "Failed with issues: Invalid JSON input.",
                "statusCode": 400
            }),
            "isBase64Encoded": False,
        }
        return response
        
