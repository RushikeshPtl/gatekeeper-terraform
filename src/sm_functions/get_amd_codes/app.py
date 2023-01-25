from sqlalchemy import create_engine, select, MetaData, Table, select,text,func
import json
import boto3
import os

lambda_client = boto3.client("lambda")

class ApiError(Exception):
    def __init__(self, code, message="Api Error"):
        self.code = code
        self.message = message
        super().__init__(self.message)

def get_credentials():
    '''
        Invokes the GetSecrets functions to fetch database credentials
    '''
    response = lambda_client.invoke(
        FunctionName=os.environ["GET_SECRET_ARN"],
        InvocationType="RequestResponse",
        Payload=json.dumps({"secret_type": "Database Credentials"}),
    )
    payload = json.load(response["Payload"])
    if "error" in payload:
        raise ApiError(
            500, f"accessing secrets manager got an error: {str(payload['error'])}")

    else:
        credentials = payload["credentials"]
        return credentials

def get_connection():
    credentials = get_credentials()
    engine = create_engine(
        "postgresql+psycopg2://{}:{}@{}/{}".format(
            credentials["username"],
            credentials["password"],
            credentials["host"],
            credentials["db"]
        )
    )
    meta = MetaData(engine)
    return engine, meta

def get_table(name, engine, meta):
    table = Table(
        name,
        meta,
        autoload = True,
        autoload_with = engine
    )
    return table

def get_amd_codes(abbr, engine, meta):
    amd_codes = get_table("organization_amd_codes", engine, meta)
    organizations = get_table("organizations", engine, meta)
    join = amd_codes.join(organizations, amd_codes.columns.organization_id == organizations.columns.id)
    stmt = select([
        amd_codes.columns.organization_id,
        amd_codes.columns.financial_class,
        amd_codes.columns.referral_provider_code,
        amd_codes.columns.default_referral_status
    ]).select_from(join).where(text(
        '''
            organizations.abbr ILIKE '{}'
        '''.format(abbr.lower())
    ))
    connection = engine.connect()
    try:
        result = connection.execute(stmt).fetchone()
    except:
        raise ApiError(500, "Something Went Wrong")
    if result:
        codes = {
            "financial_class" : result["financial_class"],
            "referral_provider_code" : result["referral_provider_code"],
            "default_referral_status" : result["default_referral_status"]
        }
        return codes
    else:
        raise ApiError(400, "Codes Not Found")

def lambda_handler(event, context):
    abbr = event.get("input", "")
    try:
        if abbr:
            engine, meta = get_connection()
            codes = get_amd_codes(abbr=abbr, engine=engine, meta=meta)
            return {
            "statusCode" : 200,
            "msg" : "Codes Fetched Successfully",
            "codes" : codes
            }
        else:
            raise ApiError(400, "Please provide abbr")
    except ApiError as e:
        return {
            "statusCode" : e.code,
            "msg" : e.message
        }
