import json
# from xmlrpc.client import Boolean
from sqlalchemy import create_engine, MetaData, Table, update, text
import boto3
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

def notify(email, phone, name, organization):
    lambda_client = boto3.client("lambda")
    send_email = lambda_client.invoke(
                            FunctionName=os.environ["SEND_EMAIL_ARN"],
                            InvocationType="Event",
                            Payload=json.dumps({
                                "type": "Referral Sent To AMD",
                                "email": email,
                                "referral_name": name,
                                "organization": organization,
                                "template_name": "ReferralSentSuccessfully"
                                }
                            ),
                        )
    try:
        sns_client = boto3.client("sns")
        phone = "+1" + phone if "+" not in phone else phone
        print(phone)
        msg = f'''
        Hello {name},
        This is Hello Hero confirming we have received your referral from {organization}. We look forward to assisting you and a member of our Admissions department will be in contact within the next 24-48 hours. If you need immediate assistance please contact out Admissions department at (800) 667-0895.
        '''
        send_sms = sns_client.publish(
            PhoneNumber = phone,
            Message = msg
        )
    except:
        pass
    return send_email

def generate_notification(generic_json):
    patient = generic_json["client"]
    email = patient["email"]
    name = patient.get("firstname", "") + " " + patient.get("lastname", "")
    organization = generic_json["referral_provider"].upper()
    phone = patient.get("mobile_phone", "")
    response = notify(email, phone, name, organization)
    dob = datetime.strptime(patient["dob"], "%Y-%m-%d").date()
    age = relativedelta(datetime.now().date(), dob).years
    if "responsible_party" in generic_json and generic_json["responsible_party"] and age < 18:
        responsible_party = generic_json["responsible_party"]
        email = responsible_party["email"]
        firstname = responsible_party.get("firstname", "")
        lastname = responsible_party.get("lastname", "")
        name = firstname + " " + lastname
        organization = generic_json["referral_provider"].upper() + " for " + generic_json["client"].get("firstname", "") + " " + generic_json["client"].get("lastname", "")
        phone = responsible_party.get("mobile_phone", "")
        response = notify(email, phone, name, organization)
    return response

def lambda_handler(event, context):
    """
        Function Name : SaveReferralRequest

        - Takes the dictionary having validation checks, original request & generic json as input.
        - For valid request => incoming request & generic json will be saved to db with failed_internal = 0 & request is passed to AMD state machine.
        - For invalid request => incoming request & generic json will be saved to db with failed_internal = 1;

        Parameters:
        -------
        event: dict

        Response:
        -------
        dict:
            - For valid request - table ids of saved referral request.
            - For Invalid Request - dictionary of issues in the request

    """
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    client = boto3.client("lambda")
    response = client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"secret_type": "Database Credentials"}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        return {
            "error_code": 500,
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
        original_request = event["original_request"]
        generic_json = event["generic_json"]
        validation_checks = event["validation_checks"]
        referral_requests = Table(
            "referral_requests", meta, autoload=True, autoload_with=engine
        )
        if "duplicate_request_ids" in event.keys() and event["msg"] == "Duplicate Request Found":
            duplicate_request_ids = tuple(event["duplicate_request_ids"])
            condition = "id in {}".format(duplicate_request_ids) if len(duplicate_request_ids) > 1 else "id = {}".format(duplicate_request_ids[0])
            update_stmt = (
                update(referral_requests)
                .where(text(
                        '''
                            {}
                        '''.format(condition))
                ).values(
                    archived = True
                )
            )
            connection.execute(update_stmt)

        referral_from="UFT" if original_request["referral_provider"]=="uft"\
                    else "Beaufort" if original_request["referral_provider"]=="beaufort"\
                    else "Interlochen" if original_request["referral_provider"]=="interlochen"\
                    else None

        status_message = "Request passed validation"
        failed_internal = False
        emr_status = 0
        if validation_checks:
            status_message = "Request failed validation"
            failed_internal = True
            emr_status = None

        if event["msg"] == "Update Request":
            update_request = (
                update(referral_requests)
                .where(referral_requests.columns.id == int(event["referral_request_id"]))
                .values(
                    referral_from = referral_from,
                    original_request = original_request,
                    internal_request = generic_json,
                    status_message = status_message,
                    error_json = validation_checks,
                    failed_internal = failed_internal,
                    emr_type = "AMD",
                    emr_status = emr_status
                )
            )
            connection.execute(update_request)
            request_id = event["referral_request_id"]
        else:
            insert_request = referral_requests.insert().values(
                referral_from = referral_from,
                original_request = original_request,
                internal_request = generic_json,
                status_message = status_message,
                error_json = validation_checks,
                failed_internal = failed_internal,
                emr_type = "AMD",
                emr_status = emr_status
            )
            result = connection.execute(insert_request)
            request_id = result.inserted_primary_key[0]

        connection.close()
        if validation_checks:
            if "token" in validation_checks:
                return {
                    "statusCode": 400,
                    "msg": validation_checks["token"][0],
                    "issues": validation_checks,
                }
            else:
                return {
                    "statusCode": 200,
                    "msg": "Success with issues",
                    "issues": validation_checks,
                }
        else:
            referral_type = generic_json["client"]["referral_type"]
            return_json = {}
            return_json["user_id"] = "U" + str(request_id)
            return_json["referral"] = []
            for referral in referral_type.split("and"):
                return_json["referral"].append(
                    {
                        "id": "R" + referral.strip()[0] + str(request_id),
                        "type": referral.strip().split(" ")[0],
                    }
                )
            # sqs = boto3.client('sqs')
            # sqs_url = 'https://sqs.us-east-1.amazonaws.com/352241563310/test-sqs-step-fn' #updaet sqs_url
            # msg = 'Adding patient & referral for request id {}'.format(request_id)
            # response = sqs.send_message(QueueUrl=sqs_url,
            #                             DelaySeconds=10,
            #                             MessageAttributes={
            #                                 'DataType': 'Number',
            #                                 'referral_request_id': request_id
            #                             },
            #                             MessageBody=(
            #                                 msg
            #                             ))

            #------Start 2nd State Machine -----------------#
            generic_json["referral_provider"] = original_request["referral_provider"]
            data = {"request_id": request_id, "generic_json": generic_json}
            client = boto3.client("stepfunctions")
            response = client.start_execution(
                stateMachineArn=os.environ["ADD_AMD_REFERRAL"],
                name="AddingToAMD"+ str(datetime.now()).replace("-", "").replace(":", "").replace(".", "").replace(" ", "") + "" + str(request_id),
                input=json.dumps(data),
            )
            generate_notification(generic_json)
            return {
                "statusCode": 200,
                "msg": "Success",
                "referral_request_id": request_id,
                "return_json": return_json,
            }
