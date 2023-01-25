import logging
import boto3
import os
import json
import redis

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def generate_zip_code_identifier(code):
    ident = f'{str(code["ZIPCode"])}_{str(code["CityName"])}_{str(code["CountyName"])}'.lower().replace(
        ' ', '_')
    return ident


def convert_image_to_zipcode(image):
    dts = image['DST']['S']
    zip_code = image['ZIPCode']['S']
    city_type = image['CityType']['S']
    county_name = image['CountyName']['S']
    utc = image['UTC']['S']
    state_name = image['StateName']['S']
    latitude = image['Latitude']['S']
    zip_type = image['ZIPType']['S']
    city_name = image['CityName']['S']
    longitude = image['Longitude']['S']
    time_zone = image['TimeZone']['S']
    state_abbr = image['StateAbbr']['S']
    area_code = image['AreaCode']['S']

    return {
        'DST': dts,
        'ZIPCode': zip_code,
        'CityType': city_type,
        'CountyName': county_name,
        'UTC': utc,
        'StateName': state_name,
        'Latitude': latitude,
        'ZIPType': zip_type,
        'CityName': city_name,
        'Longitude': longitude,
        'TimeZone': time_zone,
        'StateAbbr': state_abbr,
        'AreaCode': area_code
    }


def insert_zipcode_to_cache(redis, code):
    try:
        identifier = generate_zip_code_identifier(code)
        return redis.hmset(identifier, mapping=code)
    except Exception as e:
        raise e


def remove_zipcode_from_cache(redis, code):
    try:
        identifier = generate_zip_code_identifier(code)
        return redis.delete(identifier)
    except Exception as e:
        raise e


def lambda_handler(event, context):
    logger.info('Received Event: %s', event)

    lambda_client = boto3.client("lambda")
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({'secret_type': 'Redis Credentials'}),
    )

    payload = json.load(response["Payload"])
    if "error" in payload:
        raise Exception('Could not retrieve redis credentials')
    credentials = payload["credentials"]

    # https://redis.readthedocs.io/en/stable/examples/connection_examples.html#Connecting-to-a-redis-instance-with-username-and-password-credential-provider
    redis_creds = redis.UsernamePasswordCredentialProvider(
        credentials["username"], credentials["password"])
    redis_conn = redis.Redis(
        host=os.environ['REDIS_HOST'], port=os.environ['REDIS_PORT'], credential_provider=redis_creds, ssl=True, ssl_cert_reqs="none")

    try:
        redis_conn.ping()
        logger.info('Successfully connected to redis')
    except Exception as e:
        logger.error('Can not ping redis: %s', e)
        raise e

    for rec in event['Records']:
        logger.info('Record: %s', rec)
        if 'eventName' in rec.keys() or rec['eventName']:
            event_name = rec['eventName']
            if event_name == 'INSERT' and rec['dynamodb']['NewImage']:
                image = rec['dynamodb']['NewImage']
                code = convert_image_to_zipcode(image)
                insert_zipcode_to_cache(redis_conn, code)
            elif event_name == 'MODIFY' and rec['dynamodb']['NewImage']:
                image = rec['dynamodb']['NewImage']
                code = convert_image_to_zipcode(image)
                insert_zipcode_to_cache(redis_conn, code)
            elif event_name == 'REMOVE' and rec['dynamodb']['OldImage']:
                image = rec['dynamodb']['OldImage']
                code = convert_image_to_zipcode(image)
                remove_zipcode_from_cache(redis_conn, code)
        else:
            logger.info(
                'There is no event name skip this record: %s', json.dumps(rec))
            return {
                "statusCode": 200,
                "msg": "Success"
            }

    return {
        'statusCode': 200,
        'msg': 'success',
    }
