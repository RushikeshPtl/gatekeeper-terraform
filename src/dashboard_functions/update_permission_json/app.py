import json
import boto3
import os

def update_json(s3_key, add_permissions, remove_permissions):
    s3_client = boto3.client("s3")
    bucket = os.environ["STAGE_S3_BUCKET"] if os.environ["ENVIRONMENT"] == "DEV" else os.environ["PROD_S3_BUCKET"]
    try:
        response = s3_client.get_object(
            Bucket=bucket,
            Key=s3_key
            )
        permission_json = json.load(response["Body"])
    except:
        permission_json={}
    allowed = permission_json.get("Allowed", [])
    for permission in add_permissions:
        if permission["display_name"] not in allowed:
            allowed.append(permission["display_name"])
    for permission in remove_permissions:
        for i in range(allowed.count(permission["display_name"])):
            allowed.remove(permission["display_name"])
    permission_json["Allowed"] = allowed
    response = s3_client.put_object(
        Body = json.dumps(permission_json, sort_keys = True, indent = 4),
        Bucket = bucket,
        Key = s3_key
    )
    return {
        "statusCode" : 200,
        "msg" : "Permission json updated successfully",
    }

def lambda_handler(event, context):
    '''
        Description:
            Updates the permission json for users/role in S3 bucket
        
        Input:
            type (String) : Type of permissions i.e. role or user permissions
                            Allowed Values : "user_permissions" & "role_permissions"
            role_id (Integer) : Required for role permissions
            user_id (Integer) : Required for user permissions
            action (String) : Action to be performed on json i.e add or remove
        Output:
            - dict
    '''
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    
    permisson_type = event.get("type", "")
    error = None
    s3_key = None
    if permisson_type and permisson_type == "user_permissions":
        user_ids = event.get("user_ids", None)
        if not user_ids:
            error = "User id required"
    elif permisson_type and permisson_type == "role_permissions":
        role_id = event.get("role_id", None)
        if role_id:
            s3_key = "System/Roles/{}/role_permissions.json".format(int(role_id))
        else:
            error = "Role id required"
    else:
        error = "Please provide valid permission type"
    
    if not error:
        add_permissions = event.get("add_permissions", [])
        remove_permissions = event.get("remove_permissions", [])
        if add_permissions or remove_permissions:
            if s3_key:
                response = update_json(s3_key, add_permissions, remove_permissions)
            else:
                for user_id in user_ids:
                    s3_key = "System/Users/{}/user_permissions.json".format(int(user_id))
                    response = update_json(s3_key, add_permissions, remove_permissions)
            return response
        else:
            return {
                "statusCode" : 400,
                "msg" : "Permissions not provided"
            }
    else:
        return {
            "statusCode" : 400,
            "msg" : "Error while updating permission json",
            "error" : error
        }


    