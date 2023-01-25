import json
# from xmlrpc.client import Boolean
from sqlalchemy import create_engine, MetaData, Table, update, select
import boto3
import os
from datetime import datetime
import re
from sqlalchemy.exc import IntegrityError
import uuid
import bcrypt

def lambda_handler(event, context):
    first_name = event["first_name"]
    last_name = event["last_name"]
    email = event["email"]
    role = event["role_id"]
    phone = event.get("phone", None)
    password = event["password"]
    username = event.get("username", email)
    bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hash = bcrypt.hashpw(bytes, salt)
    error = []
    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"secret_type": "Database Credentials"}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        error.append("Error while accessing secrets manager")
    if error:
        return {
            "statusCode" : 400,
            "msg": error
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
        users = Table(
            "users",
            meta,
            autoload=True,
            autoload_with=engine
        )
        insert_user = users.insert().values(
            first_name = first_name,
            last_name = last_name,
            email = email,
            role_id = int(role),
            phone = phone,
            username = username,
            password = str(hash, 'UTF-8'),
            is_master = True,
            is_verified = True
        )
        try:
            result = connection.execute(insert_user)
            user_id = result.inserted_primary_key[0]
            statusCode = 200
            response = {
                "statusCode" : 200,
                "msg" : "User registered successfully",
                "user_id" : user_id
            }

        except IntegrityError as ig:
            statusCode = 400
            response = {
                "statusCode" : 400,
                "msg" : ig.args[0].split("DETAIL:  ")[1].strip()
            }
        return response