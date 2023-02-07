import json
import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def generate_zip_code_identifier(code):
    ident = f'{str(code["ZIPCode"])}_{str(code["CityName"])}_{str(code["CountyName"])}'.lower().replace(
        ' ', '_')
    return ident


def lambda_handler(event, context):
    bucket = os.environ["STAGE_BUCKET_NAME"] if os.environ["ENVIRONMENT"] == "dev" else os.environ["PROD_BUCKET_NAME"]
    key = os.environ["KEY"]

    s3 = boto3.resource('s3')
    obj = s3.Object(bucket, key)
    data = obj.get()['Body'].read().decode('utf-8')
    zipcodes = json.loads(data)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ZipCodes')

    for code in zipcodes:
        try:
            identifier = generate_zip_code_identifier(code)

            response = table.get_item(Key={
                'Identifier': identifier
            })
            if 'Item' not in response.keys() or not response['Item']:
                table.put_item(Item={
                    'Identifier': identifier,
                    'ZIPCode': code['ZIPCode'],
                    'ZIPType': code['ZIPType'],
                    'CityName': code['CityName'],
                    'CityType': code['CityType'],
                    'CountyName': code['CountyName'],
                    'StateName': code['StateName'],
                    'StateAbbr': code['StateAbbr'],
                    'AreaCode': code['AreaCode'],
                    'TimeZone': code['TimeZone'],
                    'UTC': str(code['UTC']),
                    'DST': code['DST'],
                    'Latitude': str(code['Latitude']),
                    'Longitude': str(code['Longitude'])
                })
        except Exception as e:
            logger.error(e)

    logger.info('zip codes are inserted')
    return {
        "statusCode": 200,
        "msg": "success",
    }
