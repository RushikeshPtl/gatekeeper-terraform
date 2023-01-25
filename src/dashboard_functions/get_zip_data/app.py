from redis import Redis
import json
import boto3
import os

response_headers = {
                    "Access-Control-Allow-Headers": "*",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "POST",
                }
lambda_client = boto3.client("lambda")

def get_credentials():
    '''
        Invokes the GetSecrets functions to fetch database credentials
    '''
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"secret_type": "Redis Credentials"}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        return payload
    else:
        credentials = payload["credentials"]
        return credentials

def lambda_handler(event, context):
    '''
        Gets the user input & returns array of all zipcodes matching user input
    '''
    credentials = get_credentials()
    if not "error" in credentials:
        redis_user = credentials["username"]
        redis_password = credentials["password"]
        redis_client = Redis(host=os.environ["EC_CLUSTER_ENDPOINT"],
                            port=6379, decode_responses=True, ssl=True,
                            username=redis_user, password=redis_password)
        
        input       = event["queryStringParameters"].get("input","") if "queryStringParameters" in event and event["queryStringParameters"] != None else ""
        output      = []
        d_cities    = []

        if input:
            match_str = str(input) + "*"
            for k in redis_client.keys(match_str):
            
                data = redis_client.hgetall(k)
                output.append(data)
                
        #get zipcode data by default city type D
        d_cities = [dt for dt in output if dt['CityType'] == 'D']
        zip_data = d_cities if d_cities else output
              
        return {
            "statusCode" : 200,
            "headers" : response_headers,
            "body" : json.dumps({
                "msg" : "Data Fetched Successfully...",
                "zip_data" : zip_data
            }),
            "isBase64Encoded": False,
        }
    else:
        return credentials