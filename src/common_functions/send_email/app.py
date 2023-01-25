import boto3
import os
import json

ses_client = boto3.client("ses")

def send_template_email(email, template_name, template_data):
    response = ses_client.send_templated_email(
        Source = os.environ["SENDER_MAIL_ID"],
        Destination = {
            "ToAddresses": [
                email,
        ],
        },
        Template = template_name,
        TemplateData = json.dumps(template_data)
    )
    return {
        "statusCode" : 200,
        "msg" : "Email sent successfully",
        "email_id": response
    }

def send_email(email, subject, msg):
    try:
        response = ses_client.send_email(
            Source= os.environ["SENDER_MAIL_ID"],
            Destination={
                "ToAddresses": [
                    email,
            ],
            },
            Message={
                "Subject": {
                    "Data": subject,
                    "Charset": "UTF-8"
                },
                "Body": {
                    "Text": {
                        "Data": msg,
                        "Charset": "UTF-8"
                    },
                }
            },
        )
    except ses_client.exceptions.MessageRejected as message_rejected:
        print(message_rejected.response)
        return {
            "statusCode" : 400,
            "msg" : "Error while sending  email ... Message rejected."
        }
    except ses_client.exceptions.MailFromDomainNotVerifiedException as domain_not_verified:
        print(domain_not_verified.response)
        return {
            "statusCode" : 400,
            "msg" : "Error while sending  email ... Domain not verified."
        }
    except ses_client.exceptions.ConfigurationSetDoesNotExistException as configuration_not_exists:
        print(configuration_not_exists.response)
        return {
            "statusCode" : 400,
            "msg" : "Error while sending  email ... Configuration set does not exist."
        }
    except ses_client.exceptions.ConfigurationSetSendingPausedException as configuration_sending_paused:
        print(configuration_sending_paused.response)
        return {
            "statusCode" : 400,
            "msg" : "Error while sending  email ... Configuration set sending paused."
        }
    except ses_client.exceptions.AccountSendingPausedException as account_sending_paused:
        print(account_sending_paused.response)
        return {
            "statusCode" : 400,
            "msg" : "Error while sending  email ... Account sending paused."
        }
    return response

def send_sms(msg, phone):
    sns_client = boto3.client("sns")
    phone = "+1" + phone if "+" not in phone else phone
    send_sms = sns_client.publish(
        PhoneNumber = phone,
        Message = msg
    )
    return

def lambda_handler(event, context):
    if "source" in event and event["source"] == "aws.events":
        print("Warm up triggered..............")
        return {
            "msg" : "Warm up triggered.............."
        }
    environment = os.environ["ENVIRONMENT"]
    endpoint = os.environ["ENDPOINT"]
    mail_type = event["type"]
    email = event["email"] if environment == "" else "rushikesh.patil@anveshak.com"
    name = event.get("name", "")
    if mail_type == "Verify Mail":
        otp = event["otp"]
        subject = "Verify mail address"
        msg = "Hi {},\nOtp to verify your email address is {}".format(name, otp)
        response = send_email(email=email, subject=subject, msg=msg)
    elif mail_type == "Forgot Password Mail":
        password_reset_token = event["password_reset_token"]
        link = "http://{}/reset-password?token='{}'".format(endpoint, password_reset_token)
        subject = "Reset Password"
        msg = "Hi {},\nPlease use below link to reset your password \n {}".format(name, link)
        response = send_email(email=email, subject=subject, msg=msg)
    elif mail_type == "Invite":
        first_login_token = event["first_login_token"]
        link = "http://{}/invite?token='{}'".format(endpoint, first_login_token)
        subject = "Invite"
        msg = "Hi {},\nPlease use below link to set password \n {}".format(name, link)
        response = send_email(email=email, subject=subject, msg=msg)
    elif mail_type == "Referral Sent To AMD":
        referral_name = event["referral_name"]
        organization = event["organization"]
        response = send_template_email(email=email, template_name=event["template_name"], template_data={"referral_name": referral_name, "organization": organization})
    elif mail_type == "Organization Token":
        subject = "Authenticaion Tokens"
        organization = event.get("organization", "")
        referral_token = event["token_data"].get("referral_token", {}).get("token", "")
        documentation_token = event["token_data"].get("documentation_token", {}).get("token", "")
        msg = "Hi {},\nAuthentication tokens for organization '{}' has been changed.\nHere are the active tokens,".format(name, organization)
        msg += "\nReferral Token : {}".format(referral_token) if referral_token else ""
        msg += "\nDocumentation Token : {}".format(documentation_token) if documentation_token else ""
        send_sms(msg, event.get("mobile", ""))
        response = send_email(email=email, subject=subject, msg=msg)
    return {
        "statusCode" : 200,
        "msg" : "Email sent successfully",
        "email_id": response
    }

