import json
from sqlalchemy import (
    create_engine,
    select,
    MetaData,
    Table,
    update
)
import uuid
import boto3
import os
from datetime import datetime, timedelta
import re

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
                "users",
                metadata,
                autoload=True,
                autoload_with=engine
            )

            select_user = select(
                table.columns.id,
                table.columns.first_name,
                table.columns.last_name
            ).where(
                table.columns.email == event["email"]
            )
            results = connection.execute(select_user).fetchall()
            if results:
                user = results[0]
                password_reset_token = uuid.uuid4().hex.upper()
                update_stmt = (
                    update(table)
                    .where(table.columns.id == user["id"])
                    .values(
                        password_reset_token = password_reset_token
                    )
                )
                try:
                    connection.execute(update_stmt)
                except:
                    return {
                        "statusCode" : 200,
                        "headers" : response_headers,
                        "body" : json.dumps({
                            "statusCode" : 200,
                            "msg" : "Something went wrong",
                        }),
                        "isBase64Encoded": False,
                    }

                response = lambda_client.invoke(
                    FunctionName=os.environ["SEND_EMAIL_ARN"],
                    InvocationType="Event",
                    Payload=json.dumps({
                        "type": "Forgot Password Mail",
                        "email": event["email"],
                        "name": user["first_name"] + " " + user["last_name"],
                        "password_reset_token" : password_reset_token
                    }),
                )
                # Create CloudWatchEvents client
                cloudwatch_events = boto3.client("events")
                # Put an event rule
                expire_time = datetime.now() + timedelta(minutes=5)
                #cron(Minutes Hours Day-of-month Month Day-of-week Year)
                minutes, hour, day, month, year = expire_time.minute, expire_time.hour, expire_time.day, expire_time.month, expire_time.year
                expression = "cron({} {} {} {} ? {})".format(str(minutes), str(hour), str(day), str(month), str(year))
                name = "EXPIRE_PASSWORD_RESET_TOKEN_{}".format(str(user["id"]))
                response = cloudwatch_events.put_rule(
                    Name=name,
                    ScheduleExpression=expression,
                    State="ENABLED"
                )
                lambda_client.add_permission(
                    FunctionName = os.environ["EXPIRE_PASSWORD_RESET_TOKEN_ARN"],
                    StatementId = str(user["id"]) + "_" + re.sub('[-:. ]', '', str(datetime.now())),
                    Action = "lambda:InvokeFunction",
                    Principal = "events.amazonaws.com",
                    SourceArn = response["RuleArn"]
                )
                response = cloudwatch_events.put_targets(
                    Rule=name,
                    Targets=[
                            {
                                "Arn": os.environ["EXPIRE_PASSWORD_RESET_TOKEN_ARN"],
                                "Id": "ExpirePasswordTokenEvent",
                                "Input": json.dumps({
                                    "user_id" : user["id"]
                            })
                            }
                        ]
                    )
                return {
                    "statusCode" : 200,
                    "headers" : response_headers,
                    "body" : json.dumps({
                        "statusCode" : 200,
                        "msg" : "Reset password link sent successfully.....",
                        "token" : password_reset_token
                    }),
                    "isBase64Encoded": False,
                }
            else:
                return {
                    "statusCode" : 200,
                    "headers" : response_headers,
                    "body" : json.dumps({
                        "statusCode" : 200,
                        "msg" : "User not found",
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