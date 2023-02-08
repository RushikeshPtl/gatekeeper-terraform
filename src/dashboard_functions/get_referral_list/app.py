import json
from sqlalchemy import create_engine, select, MetaData, Table, and_,asc,Date,text,func
import boto3
import os
# import requests

response_headers = {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET",
                }
lambda_client = boto3.client("lambda")

def escape_apostrophe(string):
    items = string.split("'")
    new_string = items[0]
    for i in items[1:]:
        new_string += "''" + i
    return new_string

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
        if is_master or (permissions and "Allowed" in permissions and "view_referral_request" in permissions["Allowed"]):
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
        FunctionName: GetReferralListByFilter

        Description:
            - This function serves the API used to list down referral requests on dashboard
            - Also, selected filters can be passed from query params

        Input:
            - event -- dict
                - QueryParams (Optional) -- dict
                    - name -- String
                    - status -- String
                    - referral from -- String
                    - limit -- Integer
                    - offset -- Integer

        Output:
            - JSON - Containing list of referral requests

    """
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
        name=event["queryStringParameters"].get("name","")
        status=event["queryStringParameters"].get("status","")
        referral=event["queryStringParameters"].get("referral","")
        token = event["queryStringParameters"].get("token","")
        date=event["queryStringParameters"].get("date","desc")
    else:
        name, status, referral, token, date = "", "Failed", "UFT", "", "desc"

    if token:
        session = authenticate(token)
        if "user_id" in session:
            user_id = session["user_id"]

            if status=="Failed":
                search_status="AND (emr_status = 2 OR emr_status IS NULL)"
            elif status=="Successful":
                search_status="AND emr_status = 1"
            elif status=="Pending":
                search_status="AND emr_status = 0"
            else:
                search_status=""

            if referral=="UFT":
                search_referral="AND referral_from = 'UFT'"
            elif referral=="Beaufort":
                search_referral="AND referral_from = 'Beaufort'"
            elif referral=="Interlochen":
                search_referral="AND referral_from = 'Interlochen'"
            else:
                search_referral=""

            response_headers = {
                                "Access-Control-Allow-Headers": "*",
                                "Access-Control-Allow-Origin": "*",
                                "Access-Control-Allow-Methods": "GET",
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
                    "headers": response_headers,
                    "body": json.dumps({
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
                metadata = MetaData(engine)
                table = Table(
                        "referral_requests",
                        metadata,
                        autoload=True,
                        autoload_with=engine
                    )
                request_error_details = Table(
                        "request_error_details",
                        metadata,
                        autoload=True,
                        autoload_with=engine
                    )

                referral_requests_notes_table = Table(
                        'referral_request_notes',
                        metadata,
                        autoload=True,
                        autoload_with=engine
                    )

                users_table = Table(
                        'users',
                        metadata,
                        autoload=True,
                        autoload_with=engine
                    )
                join = table.join(request_error_details, and_(request_error_details.columns.request_id == table.columns.id, request_error_details.columns.archived == False), isouter = True)
                name_condition = '''
                (internal_request -> 'client' ->> 'firstname') ||' '|| (internal_request -> 'client' ->> 'lastname') Ilike '%{}%'
                AND
                '''.format(escape_apostrophe(name) if name else "")
                stmt = select([
                        table.columns.id,
                        table.columns.referral_from,
                        table.columns.original_request,
                        table.columns.internal_request,
                        table.columns.emr_type,
                        table.columns.emr_status,
                        table.columns.error_json,
                        request_error_details.columns.url,
                        request_error_details.columns.payload,
                        request_error_details.columns.error_type,
                        request_error_details.columns.error_details,
                        request_error_details.columns.error_reason,
                        table.columns.note,
                        table.columns.created_at,
                    ]).select_from(join).where(text(
                        """
                            {} referral_requests.archived = false
                            {}
                            {}
                        """.format(name_condition,search_status,search_referral)
                        )).limit(
                        event["queryStringParameters"].get("limit",10) if "queryStringParameters" in event and event["queryStringParameters"] != None else 10
                        ).offset(
                        event["queryStringParameters"].get("offset",0) if "queryStringParameters" in event and event["queryStringParameters"] != None else 0
                        ).order_by(table.columns.created_at.desc() if date == "desc" else table.columns.created_at.asc())

                count_stmt=select([func.count(table.columns.id.distinct())]).select_from(join).where(text(
                        """
                            {} referral_requests.archived = false
                            {}
                            {}
                        """.format(name_condition,search_status,search_referral)
                        ))

                connection = engine.connect()
                try:
                    referral_results = connection.execute(stmt).fetchall()
                    count_results = connection.execute(count_stmt).fetchall()
                except Exception as e:
                    return {
                            "statusCode": 200,
                            "headers": response_headers,
                            "body":json.dumps({
                                "statusCode": 200,
                                "msg": "something went wrong",
                                "error_response": str(e)
                            }),
                            "isBase64Encoded": False,
                        }
                response={"referral_request":[]}
                if len(referral_results)==0:
                    return {
                        "statusCode": 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "record not found",
                            "response":response
                        }),
                        "isBase64Encoded": False,
                    }
                count=count_results[0][0]

                ids=[val['id'] for val in referral_results]
                join = referral_requests_notes_table.join(users_table, and_(referral_requests_notes_table.columns.added_by == users_table.columns.id, referral_requests_notes_table.columns.archived == False), isouter = True)
                condition = "IN {}".format(tuple(ids)) if len(ids) > 1 else "= {}".format(ids[0])
                stmt = select([
                            referral_requests_notes_table.columns.id,
                            referral_requests_notes_table.columns.referral_request_id,
                            referral_requests_notes_table.columns.added_by,
                            referral_requests_notes_table.columns.archived,
                            referral_requests_notes_table.columns.note,
                            referral_requests_notes_table.columns.created_at,
                            users_table.columns.first_name,
                            users_table.columns.last_name,
                        ]).select_from(join).where(text(
                            """
                                referral_request_notes.referral_request_id {}
                                AND referral_request_notes.archived = false
                            """.format(condition)
                            )).order_by(referral_requests_notes_table.columns.created_at.desc())
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
                                "error_response": str(e)
                            }),
                            "isBase64Encoded": False,
                        }

                for result in referral_results:
                    firstname = result["internal_request"]["client"]["firstname"] if "firstname" in result["internal_request"]["client"] and result["internal_request"]["client"]["firstname"] else ""
                    lastname = result["internal_request"]["client"]["lastname"] if "lastname" in result["internal_request"]["client"] and result["internal_request"]["client"]["lastname"] else ""
                    if len(result["internal_request"]["responsible_party"])>3:
                        resp_firstname = result["internal_request"]["responsible_party"]["firstname"] if "firstname" in result["internal_request"]["responsible_party"] and result["internal_request"]["responsible_party"]["firstname"] else ""
                        resp_lastname = result["internal_request"]["responsible_party"]["lastname"] if "lastname" in result["internal_request"]["responsible_party"] and result["internal_request"]["responsible_party"]["lastname"] else ""
                        resp_party = resp_firstname +" " + resp_lastname
                    else:
                        resp_party = firstname + " " + lastname

                    status = "Successful" if result["emr_status"] == 1 else "Pending" if result["emr_status"] == 0 else "Failed"
                    id=result["id"]
                    note=[{"note":x["note"],"added_by":x["first_name"]+" "+x["last_name"], "created_at":str(x["created_at"].date())} for x in results if int(x["referral_request_id"]) == int(id)]
                    firstname = result["internal_request"]["client"]["firstname"] if "firstname" in result["internal_request"]["client"] and result["internal_request"]["client"]["firstname"] else ""
                    lastname = result["internal_request"]["client"]["lastname"] if "lastname" in result["internal_request"]["client"] and result["internal_request"]["client"]["lastname"] else ""
                    patient = firstname + " " + lastname
                    respo_party = resp_party
                    date_recieved = result["created_at"].date()
                    referral_from = result["referral_from"]
                    data = result["original_request"]
                    error = {
                        "error_json" : result["error_json"],
                        "url" : result["url"],
                        "payload" : result["payload"],
                        "error_type" : result["error_type"],
                        "error_details" : result["error_details"],
                        "error_reason" : result["error_reason"]
                    }
                    data.pop("token")
                    if "caseId" in data:
                        data.pop("caseId")
                    record={
                    "id" : id,
                    "referral_from" : referral_from,
                    "patient" : patient,
                    "note":note,
                    "request_ip":event['requestContext']['identity']['sourceIp'],
                    "responsible_party" : respo_party,
                    "status" : status,
                    "date_recieved" : str(date_recieved),
                    "error" : error,
                    "data" : data
                    }
                    response["referral_request"].append(record)
                return {
                        "statusCode": 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "records fetched",
                            "total_records": count,
                            "response": response
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