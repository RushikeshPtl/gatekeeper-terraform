import requests
import json
import os

def lambda_handler(event, context):
    """
        Function Name : ValidateRecaptcha

        - This function will validate google recaptcha.

        Response:
        -----
        dict
    """
    body=json.loads(event['body'])
    response_headers = {
                        "Access-Control-Allow-Headers": "*",
                        "Access-Control-Allow-Origin": "*",
                        "Access-Control-Allow-Methods": "POST",
                    }
    url = os.environ["RECAPTCHA_URL"]
    # "https://www.google.com/recaptcha/api/siteverify"
    payload={
        'secret': os.environ["RECAPTCHA_SECRET_KEY"],
        'response': body['response']
        }
    response = requests.request("POST", url, data=payload)
    resp=json.loads(response.text)
    error=""
    if "error-codes" in resp:
        if "missing-input-secret" in resp['error-codes']:
            error= "The secret parameter is missing."
        if "invalid-input-secret" in resp['error-codes']:
            error= "The secret parameter is invalid or malformed."
        if "missing-input-response" in resp['error-codes']:
            error= "The response parameter is missing."
        if "invalid-input-response" in resp['error-codes']:
            error= "The response parameter is invalid or malformed."
        if "bad-request" in resp['error-codes']:
            error= "The request is invalid or malformed."
        if "timeout-or-duplicate" in resp['error-codes']:
            error= "The response is no longer valid: either is too old or has been used previously."

    if resp['success']==True:
        return {
            "statusCode": 200,
            "headers": response_headers,
            "body":json.dumps({
                "msg": "success",
                "response":resp
            }),
            "isBase64Encoded": False,
        }
    else:
        return {
            "statusCode": 200,
            "headers": response_headers,
            "body":json.dumps({
                "msg": "error",
                "response":resp,
                "error_msg":error
            }),
            "isBase64Encoded": False,
        }