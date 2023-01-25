from sqlalchemy import create_engine, select, MetaData, Table, select,text,func
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

    if "queryStringParameters" in event and event["queryStringParameters"] != None:
        name = event["queryStringParameters"].get("name","")
        archived = event["queryStringParameters"].get("archived","")
        role = event["queryStringParameters"].get("role","")
        token = event["queryStringParameters"].get("token","")
    else:
        name, archived, role, token = "", "", "", ""

    if token:
        session = authenticate(token)
        if "user_id" in session:
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

            if archived=="True":
                search_archived="AND (archived = 'True')"
            elif archived=="False":
                search_archived="AND (archived = 'False')"
            else:
                search_archived=""

            if role is not "":
                search_role="AND (role = '{}')".format(role)
            else:
                search_role=""

            sp_name=name.split(" ")
            opr="AND"
            if len(sp_name) == 1 and sp_name[0] == "":
                firstname, lastname = "%", "%"
            elif len(sp_name) < 2:
                firstname, lastname = sp_name[0], sp_name[0]
                opr = "OR"
            else:
                firstname, lastname = sp_name[0], sp_name[1]

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

                users_table = Table(
                        'users',
                        metadata,
                        autoload=True,
                        autoload_with=engine
                    )

                roles_table = Table(
                        'roles',
                        metadata,
                        autoload=True,
                        autoload_with=engine
                    )

                joined_table = roles_table.join(users_table, roles_table.columns.id == users_table.columns.role_id)
                stmt = select(
                    [
                        users_table.columns.id,
                        users_table.columns.first_name,
                        users_table.columns.last_name,
                        users_table.columns.email,
                        users_table.columns.username,
                        users_table.columns.archived,
                        users_table.columns.is_verified,
                        roles_table.columns.role
                        ]).select_from(joined_table).where(text(
                        """
                            (first_name Ilike '{}'
                            {} last_name Ilike '{}')
                            AND role_level > {}
                            {}
                            {}

                        """.format(firstname,opr, lastname, session["role_level"], search_archived, search_role)
                )).limit(
                event["queryStringParameters"].get("limit",10) if "queryStringParameters" in event and event["queryStringParameters"] != None else 10
                ).offset(
                event["queryStringParameters"].get("offset",0) if "queryStringParameters" in event and event["queryStringParameters"] != None else 0
                )

                count_stmt=select([func.count(users_table.columns.id)]).select_from(joined_table).where(text(
                        """
                            (first_name Ilike '{}'
                            {} last_name Ilike '{}')
                            AND role_level > {}
                            {}
                            {}
                        """.format(firstname, opr, lastname, session["role_level"], search_archived, search_role)
                        ))

                connection = engine.connect()
                try:
                    results = connection.execute(stmt).fetchall()
                    count_results = connection.execute(count_stmt).fetchall()
                except Exception as e:
                    return {
                            "statusCode": 200,
                            "headers": response_headers,
                            "body":json.dumps({
                                "statusCode": 200,
                                "msg": "Something went wrong",
                                "error_response":e
                            }),
                            "isBase64Encoded": False,
                        }

                if len(results)==0:
                    return {
                            "statusCode": 200,
                            "headers": response_headers,
                            "body":json.dumps({
                                "statusCode": 200,
                                "msg": "Records not found"
                            }),
                            "isBase64Encoded": False,
                        }

                count=count_results[0][0]
                records=[]
                for re in results:
                    user={
                        "id":re["id"],
                        "first_name":re["first_name"],
                        "last_name":re["last_name"],
                        "email":re["email"],
                        "username":re["username"],
                        "role":re["role"],
                        "is_verified":re["is_verified"],
                        "archived":re["archived"]
                        }
                    records.append(user)

                return {
                        "statusCode": 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "Records fetched",
                            "total_records": count,
                            "records":records
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