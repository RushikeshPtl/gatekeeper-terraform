import json
import boto3
from sqlalchemy import create_engine, MetaData, Table, select, update
import os

response_headers = {
    "Access-Control-Allow-Headers": "*",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS"
}
lambda_client = boto3.client("lambda")

def log_error(data):
    response = lambda_client.invoke(
        FunctionName=os.environ["LOG_REQUEST_ERROR_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps(data),
    )
    payload = json.load(response["Payload"])
    if not payload or "error" in payload:
        return {
            "statusCode": 500,
            "msg": "error while accessing secrets manager",
            "error": payload["error"] if payload else "",
        }
    else:
        return "Error Logged"


def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    print(event)
    if "is_validate" in event:
        data = {
            "error_type" : "Internal Error",
            "error_details": event["Cause"] if "Cause" in event else event["error_exception"] if "error_exception" in event else "",
            "error_reason": event["error_reason"],
            "request_id": event["request_id"],
            "payload": event["payload"]
        }
        log_error(data=data)
        return {
            "statusCode" : 500,
            "headers" : response_headers,
            "body" : json.dumps({
                "statusCode": 500,
                "msg": "Internal server error"
            }),
            "isBase64Encoded": False,
        }
    try:
        response = lambda_client.invoke(
            FunctionName=os.environ["GET_SECRET_ARN"],
            InvocationType="RequestResponse",
            Payload=json.dumps({"secret_type": "Database Credentials"}),
        )
        payload = json.load(response["Payload"])
        if "error" in payload:
            return {
                "statusCode": 500,
                "msg": "error while accessing secrets manager",
                "error": payload["error"],
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
            meta = MetaData(engine)
            connection = engine.connect()
            request_id = event["request_id"]
            referral_requests = Table(
                "referral_requests", meta, autoload=True, autoload_with=engine
            )
            select_stmt = select(referral_requests.columns.emr_entries).where(
                referral_requests.columns.id == event["request_id"]
            )
            request_data = connection.execute(select_stmt).fetchone()
            emr_entries = request_data[0] if request_data[0] else 0
            if "error_json" in event.keys() or "error" in event.keys():
                if "error_json" in event.keys():
                    json_data = event["error_json"]
                else:
                    if type(event["error"]) == dict:
                        request_id = event["body"]["data"]["request_id"]
                        json_data = event["error"]
                    else:
                        json_data = {"msg": event["msg"]}
                emr_status = 2
                msg = "Process ended with error"
            else:
                json_data = {}
                json_data["msg"] = "Referral Added Successfully"
                json_data["Patient ID"] = event["patient_id"] if "patient_id" in event else 0
                json_data["Referral Ids"] = event["referral_ids"] if "referral_ids" in event else 0
                emr_status = 1
                msg = "Amd referral added successfully"
            update_stmt = (
                update(referral_requests)
                .where(referral_requests.columns.id == int(request_id))
                .values(
                    emr_response=json_data,
                    emr_entries=emr_entries + 1,
                    emr_status=emr_status,
                )
            )
            connection.execute(update_stmt)

            if msg == "Process ended with error":
                data = {
                    "request_id" : int(request_id),
                    "error_type" : "Error while calling AMD API",
                    "error_details" : json_data,
                    "url" : event.get("url", ""),
                    "payload" : event.get("payload", {})
                }
                log_error(data=data)

            return {"statusCode": 200, "msg": msg}
    except Exception as e:
        reason = "Error while sending fallback response"
        data = {
            "request_id" : event.get("request_id", None),
            "error_details" : str(e),
            "url" : event.get("url", ""),
            "payload" : event.get("payload", {}),
            "error_reason": reason,
        }
        log_error(data=data)
        return {"statusCode": 500, "msg": reason}
