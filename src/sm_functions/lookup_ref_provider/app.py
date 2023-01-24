import json
import boto3
import requests
import os
import datetime

def lambda_handler(event, context):
    client = boto3.client("lambda")
    response = client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"secret_type": "AMD Token"}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        return {
            "error_code": 500,
            "msg": "Error while accessing secrets manager",
            "error": payload["error"],
        }
    else:
        token     = payload["token"]
        webserver = payload["webserver"]
        cookies   = {"token": token}
        headers   = {"Content-Type": "application/json", "Accept": "application/json"}
        code      = event["queryStringParameters"].get("code", "") if event["queryStringParameters"].get("code", "") else ""
        resource  = event.get("resource", "")

        response_headers = {
                                "Access-Control-Allow-Headers": "*",
                                "Access-Control-Allow-Origin": "*",
                                "Access-Control-Allow-Methods": "POST, OPTIONS"
                            }
        if code:
            pdata = {
                "ppmdmsg": {
                    "@action": "lookuprefprovider",
                    "@class": "api",
                    "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
                    "@exactmatch": "-1",
                    "@code": code,
                    "@page": "1",
                    "@nocookie": "0"
                }
            }
            resp = requests.post(
                webserver, headers=headers, cookies=cookies, json=pdata
            )
            response         = json.loads(resp.text)
            ref_provider     = []
          
            if response["PPMDResults"]["Results"]:

                refproviderlist = response["PPMDResults"]["Results"]["refproviderlist"]["refprovider"]
                
                if resource == "Internal Request":
                    #return refrerring provider id from code
                    provider_id = refproviderlist["@id"]
                    return {
                        "statusCode": "200",
                        "msg" : "Referral Provider Fetched Successfully",
                        "referral_provider_id" : provider_id
                    }
                else:
                    #generate and return refrerring provider list in response
                    ref_provider.append({
                        "id" : refproviderlist["@id"],
                        "code": refproviderlist["@code"],
                        "name": refproviderlist["@name"]
                    })
                    if ref_provider:
                        
                        return {
                            "statusCode" : 200,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "msg" : "Referring Providers list Fetched Successfully",
                                "referring_provider" : ref_provider
                            })
                        }
                    else:
                        return {
                            "statusCode" : 200,
                            "headers" : response_headers,
                            "body" : json.dumps({
                                "msg" : "Referring Provider list Not Found"
                            })
                        }     
            else:
                return {
                    "statusCode": "400",
                    "headers" : response_headers,
                    "body" : json.dumps({
                        "statusCode": "400",
                        "msg" : "Referral Provider not found for the code",
                        "error": "Referral Provider not found for the code"
                    })
                }
        else:
             return {
                    "statusCode": "400",
                    "headers" : response_headers,
                    "body" : json.dumps({
                        "statusCode": "400",
                        "msg" : "Code Not Found",
                        "error": "Code Not Found"
                    })
                }

