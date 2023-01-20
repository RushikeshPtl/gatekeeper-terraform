import os


HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,x-api-key",
    "Access-Control-Allow-Methods": os.environ.get("ALLOWED_METHODS"),
    "Access-Control-Allow-Credentials": True,
    "Content-Type": "application/json",
    "Accept": "application/json"
}


def get_headers():
    """
    Get the headers to add to response data
    """

    return HEADERS
