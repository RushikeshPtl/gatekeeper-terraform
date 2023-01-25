import re

def lambda_handler(event, context):
    """

        Function Name : FindRelationshipID

        - Takes relationship of client with member as input
        - Looks for equivalent hipaa relationship id & returns the same

        Parameters
        -------
        event: dict having relationship of client with member as "input"

        Response
        -------
        dict: With status code & hipaa id

    """
    relationships = {
        "SELF": {"std" : "1", "HIPAA Relationship": {"SELF": "18"}},
        "SPOUSE": {"std" : "2", "HIPAA Relationship": {"SPOUSE": "01"}},
        "CHILD": {"std" : "3",
            "HIPAA Relationship": {
            "ADOPTED CHILD": "09",
            "FOSTER CHILD": "10",
            "STEPSON OR STEPDAUGHTER": "17",
            "CHILD": "19",
            "EMANCIPATED MINOR": "36",
            "CHILD WHERE INSURED HAS NO FINANCIAL RESPONSIBILITY": "43",
            }
        },
        "OTHER": {"std" : "4",
            "HIPAA Relationship": {
            "GRANDFATHER OR GRANDMOTHER": "04",
            "GRANDSON OR GRANDDAUGHTER": "05",
            "NEPHEW OR NIECE": "07",
            "WARD": "15",
            "EMPLOYEE": "20",
            "UNKNOWN": "21",
            "HANDICAPPED DEPENDENT": "22",
            "SPONSORED DEPENDENT": "23",
            "DEPENDENT OF A MINOR DEPENDENT": "24",
            "SIGNIFICANT OTHER": "29",
            "MOTHER": "32",
            "FATHER": "33",
            "OTHER ADULT": "34",
            "ORGAN DONOR": "39",
            "CADAVER DONOR": "40",
            "INJURED PLAINTIFF": "41",
            "LIFE PARTNER": "53",
            "OTHER RELATIONSHIP": "G8"
            }
        },
    }
    input = re.sub(" +", " ", event["input"].lower())
    std = relationships["SELF"]["std"]
    hipaa = relationships["SELF"]["HIPAA Relationship"]["SELF"]
    if input == "self":
        hipaa = relationships["SELF"]["HIPAA Relationship"]["SELF"]
    elif "spouse" in input:
        std = relationships["SPOUSE"]["std"]
        hipaa = relationships["SPOUSE"]["HIPAA Relationship"]["SPOUSE"]
    elif ("son" in input or "daughter" in input or "child" in input) and "grand" not in input:
        std = relationships["CHILD"]["std"]
        if "adopted" in input:
            hipaa = relationships["CHILD"]["HIPAA Relationship"]["ADOPTED CHILD"]
        elif "foster" in input:
            hipaa = relationships["CHILD"]["HIPAA Relationship"]["FOSTER CHILD"]
        elif "step" in input:
            hipaa = relationships["CHILD"]["HIPAA Relationship"]["STEPSON OR STEPDAUGHTER"]
        elif "child where insured has no financial responsibility" in input:
            std = relationships["CHILD"]["std"]
            hipaa = relationships["CHILD"]["HIPAA Relationship"]["CHILD WHERE INSURED HAS NO FINANCIAL RESPONSIBILITY"]
        else:
            hipaa = relationships["CHILD"]["HIPAA Relationship"]["CHILD"]
    elif "emancipated" in input:
        std = relationships["CHILD"]["std"]
        hipaa = relationships["CHILD"]["HIPAA Relationship"]["EMANCIPATED MINOR"]
    elif "grandmother" in input or "grandfather" in input:
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["GRANDFATHER OR GRANDMOTHER"]
    elif "grandson" in input or "granddaughter" in input:
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["GRANDSON OR GRANDDAUGHTER"]
    elif "nephew" in input or "niece" in input:
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["NEPHEW OR NIECE"]
    elif "ward" in input:
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["WARD"]
    elif input == "employee":
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["EMPLOYEE"]
    elif "handicapped" in input:
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["HANDICAPPED DEPENDENT"]
    elif "sponsored" in input:
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["SPONSORED DEPENDENT"]
    elif input == "mother":
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["MOTHER"]
    elif input == "father":
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["FATHER"]
    elif input == "organ donor":
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["ORGAN DONOR"]
    elif input == "cadaver donor":
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["CADAVER DONOR"]
    elif input == "life partner":
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["LIFE PARTNER"]
    elif input == "dependent of a minor dependent":
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["DEPENDENT OF A MINOR DEPENDENT"]
    elif "adult" in input:
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["OTHER ADULT"]
    elif input == "injured plaintiff":
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["INJURED PLAINTIFF"]
    elif input == "unknown":
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["UNKNOWN"]
    elif input == "significant other":
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["SIGNIFICANT OTHER"]
    else:
        std = relationships["OTHER"]["std"]
        hipaa = relationships["OTHER"]["HIPAA Relationship"]["OTHER RELATIONSHIP"]

    return {"status_code": 200, "hipaa_id": hipaa, "std": std}
