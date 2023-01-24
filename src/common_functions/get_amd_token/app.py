import json
import requests
import boto3
import datetime
from botocore.exceptions import ClientError
import os

lambda_client = boto3.client("lambda")
def get_amd_creds():
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"secret_type": "AMD Creds"}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        return {
            "error_code": 500,
            "msg": "Log Error",
            "error_type" : "Internal Error",
            "error_details": payload["error"],
            "error_reason": "Error while accessing secrets manager in AddPatientDetails",
        }
    else:
        return payload["credentials"]

def getToken():

    url = (
        "https://partnerlogin.advancedmd.com/practicemanager/xmlrpc/processrequest.aspx"
    )
    credentials = get_amd_creds()
    if not "error_code" in credentials:
        myobj = {
            "ppmdmsg": {
                "@action": "login",
                "@class": "login",
                "@msgtime": str(datetime.datetime.strftime(datetime.datetime.now(), '%m/%d/%Y %I:%M:%S %p')),
                "@username": credentials["username"],
                "@psw": credentials["password"],
                "@officecode": credentials["officecode"],
                "@appname": "HELLOHERO",
            }
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        resp1 = requests.post(url, headers=headers, json=myobj)

        res = json.loads(resp1.text)
        webserver = (
            res["PPMDResults"]["Results"]["usercontext"]["@webserver"]
            + "/"
            + "xmlrpc/processrequest.aspx"
        )

        resp2 = requests.post(webserver, headers=headers, json=myobj)

        res2 = json.loads(resp2.text)
        token = res2["PPMDResults"]["Results"]["usercontext"]["#text"]
        root_url = res2["PPMDResults"]["Results"]["usercontext"]["@webserver"]
        pmapiredirecturl = res2["PPMDResults"]["Results"]["usercontext"]["@pmapiredirecturl"]
        webserver = root_url + "/" + "xmlrpc/processrequest.aspx"
        return token, webserver, pmapiredirecturl
    else:
        return credentials


def lambda_handler(event, context):
    """
        Function Name : GetAMDToken

        - Calls AMD login API for webserver to hit further requests.
        - Hits same login request to webserver to get the token.
        - Creates or updates the secret to store the token.

        Parameters:
        -------
        None

        Response:
        -------
        dict with status code
    """

    session = boto3.session.Session()
    region_name = "us-east-1"
    client = session.client(service_name="secretsmanager", region_name=region_name)
    token, webserver, pmapiredirecturl = getToken()
    secret = {"token" : token, "webserver" : webserver, "pmapiredirecturl" : pmapiredirecturl}
    # environment = os.environ["ENVIRONMENT"]
    secret_name = os.environ["AMD_SECRET_NAME"]
    print(secret_name)
    try:
        get_secret = client.get_secret_value(SecretId=secret_name)

        response = client.update_secret(
            SecretId = secret_name, 
            SecretString = json.dumps(secret)
        )

        return {
            "status_code" : 200,
            "msg" : "Secret Updated Successfully"
        }

    except ClientError:
        current_time = datetime.datetime.now()

        response = client.create_secret(
            Name = secret_name,
            SecretString = json.dumps(secret),
        )

        return {
            "status_code" : 200,
            "msg" : "Secret Created Successfully"
        }
