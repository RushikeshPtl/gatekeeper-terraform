import json
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    update
)
import boto3
import os

def lambda_handler(event, context):
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
        user_id = event["user_id"]
        update_stmt = (
                    update(table)
                    .where(table.columns.id == int(user_id))
                    .values(
                        password_reset_token = None
                    )
                )
        try:
            connection.execute(update_stmt)
        except:
            print("Something went wrong for user {}".format(user_id))
            return {
                "statusCode" : 200,
                "msg" : "Something went wrong",
                "user_id" : user_id
            }
        return {
                "statusCode" : 200,
                "msg" : "Password reset token removed",
                "user_id" : user_id
            }