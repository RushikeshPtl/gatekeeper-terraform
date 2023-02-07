import json
# from xmlrpc.client import Boolean
from sqlalchemy import create_engine, MetaData, Table, update, select
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
                    "msg": error
                }),
                "isBase64Encoded": False,
            }
    else:
        is_master = payload.get("is_master", False)
        permissions = payload.get("permissions", "")
        if resource == "Internal Request" or is_master or ("Allowed" in permissions and "edit_user_permissions" in permissions["Allowed"]):
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

def get_role_permissions(role_id, token):
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_ROLE_PERMISSIONS"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"resource": "Internal Request", "queryStringParameters": {"role_id": role_id, "token" : token}}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        return payload
    elif "body" in payload:
        body = json.loads(payload["body"])
        if "permissions" in body:
            permissions_list = []
            for category, permissions in body["permissions"].items():
                for permission in permissions:
                    permissions_list.append(permission)
            return permissions_list
        else:
            return body
    else:
        return payload

def lambda_handler(event, context):
    if is_json(event):
        if not isinstance(event, dict):
            event = json.loads(event)
        if "source" in event and event["source"] == "aws.events":
            print("Warm up triggered..............")
            return {
                "msg" : "Warm up triggered.............."
            }

        resource = event.get("resource", "")
        print("Resource ----------------------> ", resource)
        event = json.loads(event["body"]) if "body" in event else event
        token = event.get("token", "")
        if token:
            session = authenticate(token = token, resource = resource)
            if "user_id" in session:
                user_ids = [event["user_id"]] if "user_id" in event else event["user_ids"] if "user_ids" in event else []
                if "role_id" in event:
                    add_permissions = get_role_permissions(event["role_id"], token)

                    if isinstance(add_permissions, dict):
                        return {
                            "statusCode" : 500,
                            "msg" : "Error while fetching role permissions",
                            "error" : add_permissions["error"] if "error" in add_permissions else add_permissions["msg"]
                        }
                    remove_permissions = []
                else:
                    add_permissions = event.get("add_permissions", [])
                    remove_permissions = event.get("remove_permissions", [])
                if user_ids:
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
                        user_permissions = Table(
                            "user_permissions",
                            meta,
                            autoload = True,
                            autoload_with = engine
                        )
                        if add_permissions:
                            for user_id in user_ids:
                                select_permissions = select(
                                        user_permissions.columns.permission_id
                                    ).where(user_permissions.columns.user_id == user_id)
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
                                        assign_permission = user_permissions.insert().values(
                                            user_id = user_id,
                                            permission_id = permission_id
                                        )
                                        try:
                                            result = connection.execute(assign_permission)
                                            existing_permissions.append(permission_id)
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
                        if remove_permissions:
                            for user_id in user_ids:
                                for permission in remove_permissions:
                                    permission_id = permission["id"]
                                    remove_permission = user_permissions.delete().where(
                                        user_permissions.columns.user_id == user_id,
                                        user_permissions.columns.permission_id == permission_id
                                    )
                                    try:
                                        result = connection.execute(remove_permission)
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
                        add_permission_list = [{"id" : permission["id"], "display_name" : permission["display_name"]} for permission in add_permissions]
                        remove_permission_list = [{"id" : permission["id"], "display_name" : permission["display_name"]} for permission in remove_permissions]
                        if add_permission_list or remove_permission_list:
                            update_json = lambda_client.invoke(
                                FunctionName=os.environ["UPDATE_PERMISSION_JSON_ARN"],
                                InvocationType="Event",
                                Payload=json.dumps({
                                    "type" : "user_permissions",
                                    "user_ids" : user_ids,
                                    "add_permissions" : add_permission_list,
                                    "remove_permissions" : remove_permission_list
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
                                    "msg": "Permissions not provided",
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
                                "msg": "Atleast one permission should be assigned"
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
                "statusCode": 200
            }),
            "isBase64Encoded": False,
        }
        return response
        
