from sqlalchemy import create_engine, MetaData, Table, update
import psycopg2
import os
import json
import boto3

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
                "body" : json.dumps({
                    "statusCode": 500,
                    "msg": "error while accessing secrets manager",
                    "error": payload["error"],
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

            token=event.get("token","")
            s3_client = boto3.client('s3')
            bucket = os.environ["STAGE_S3_BUCKET"] if os.environ["ENVIRONMENT"] == "DEV" else os.environ["PROD_S3_BUCKET"]
            try:
                response = s3_client.get_object(
                            Bucket=bucket,
                            Key='session_json'
                            )

                session_json = json.load(response["Body"])
                token = [key for key,value in session_json.items() if key == token]
                if len(token)==0:
                    return {
                        "statusCode": 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "Please send valid token",
                        }),
                        "isBase64Encoded": False,
                    }

                user_id=session_json[token[0]]
            except:
                return {
                        "statusCode": 200,
                        "headers": response_headers,
                        "body":json.dumps({
                            "statusCode": 200,
                            "msg": "Something went wrong with s3",
                        }),
                        "isBase64Encoded": False,
                    }

            user_id=session_json[token[0]]
            update_stmt = (
                        update(table)
                        .where(table.columns.id == user_id)
                        .values(
                                is_verified = True
                                )
                            )
            connection.execute(update_stmt)
            return {
                    "statusCode": 200,
                    "headers": response_headers,
                    "body":json.dumps({
                            "statusCode": 200,
                            "msg": "Email Verified",
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