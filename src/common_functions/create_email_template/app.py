import boto3
import json

def lambda_handler(event, context):
    template_name = event.get("template_name", "")
    text_part = event.get("text_part", "")
    html_part = event.get("html_part", "")
    subject_part = event.get("subject_part", "")

    if template_name and html_part and subject_part:
        ses_client = boto3.client("ses")
        try:
            create_template = ses_client.create_template(
                Template={
                    'TemplateName': template_name,
                    'SubjectPart': subject_part,
                    'TextPart': text_part,
                    'HtmlPart': html_part
                }
            )
            return {
                "statusCode" : 200,
                "msg" : "Template created successfully"
            }
        except:
            return {
                "statusCode" : 500,
                "msg" : "Error while creating template"
            }
    else:
        return {
            "statusCode" : 400,
            "msg" : "Template name, html part & subject part must be provided"
        }