import json

# from xmlrpc.client import Boolean
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    Integer,
    String,
    JSON,
    Text,
    Boolean,
    DateTime,
    text,
    ForeignKey,
    UniqueConstraint,
    update
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import boto3
import os


def get_table(name, meta, engine):
    tb = Table(
        name,
        meta,
        autoload=True,
        autoload_with=engine
    )

    return tb


def lambda_handler(event, context):
    """
        Function Name : ReadWriteDatabase

        - This function will migrate the database changes

        Response:
        -----
        dict
    """
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
        print(credentials)
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
        print("Engine Connected..........................................")
        uuid_ext = 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'
        engine.execute(uuid_ext)

                    ###  Referral Requests Table  ###

        if not engine.dialect.has_table(connection, "referral_requests"):
            print("Creating referral_requests Table..........................................")
            '''
                If referral_requests table is not in database then it will be created along with triggers to set updated_at timestamp
            '''
            updated_at_function = '''
                CREATE OR REPLACE FUNCTION trigger_set_timestamp()
                RETURNS TRIGGER AS $$
                BEGIN
                NEW.updated_at = NOW();
                RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
            '''
            connection.execute(updated_at_function)

            referral_requests = Table(
                "referral_requests",
                meta,
                Column("id", Integer, primary_key=True),
                Column("referral_from", String(255)),
                Column("original_request", JSON),
                Column("internal_request", JSON),
                Column("status_message", Text),
                Column("error_json", JSON),
                Column("failed_internal", Boolean),
                Column("emr_type", String(255)),
                Column("emr_status", Integer),
                Column("emr_response", JSON),
                Column("emr_entries", Integer, server_default = "0"),
                Column("archived", Boolean, server_default = "0"),
                Column(
                    "created_at", DateTime(timezone=True), server_default=func.now()
                ),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now()),
            )
            meta.create_all(engine)

            updated_at_trigger = '''
                CREATE TRIGGER set_timestamp
                BEFORE UPDATE ON referral_requests
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(updated_at_trigger)
        else:
            print("Table referral_requests already exists..........................................")

                    ###  Log Referral Requests Table  ###

        if not engine.dialect.has_table(connection, "log_referral_requests"):
            '''
                If log_referral_requests table is not in database then it will be created.
            '''
            print("Creating log_referral_requests Table..........................................")
            log_referral_requests = Table(
                "log_referral_requests",
                meta,
                Column(
                    "id",
                    UUID(as_uuid=True),
                    server_default=text("uuid_generate_v4()"),
                    primary_key=True,
                ),
                Column("referral_request_id", Integer),
                Column("changetype", String(255)),
                Column(
                    "changedate", DateTime(timezone=True), server_default=func.now()
                ),
            )
            meta.create_all(engine)
        else:
            print("Table log_referral_requests already exist..........................................")

                    ###  Trigger To Record logs of referral request  ###

        triggers = [result[0] for result in connection.execute("SELECT trigger_name FROM information_schema.triggers").fetchall()]
        if "log_request_trg" not in triggers:
            '''
                If trigger to record logs of referral_request is not present in database then it will be created
            '''

            print("Creating trigger to record referral_request logs..........................................")

            log_trigger_function = """
                CREATE OR REPLACE FUNCTION log_request() RETURNS TRIGGER AS $log_request_trg$
                    BEGIN
                        IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
                            INSERT INTO log_referral_requests (referral_request_id, changetype) VALUES(New.id, TG_OP);
                        ELSIF (TG_OP = 'DELETE') THEN
                            INSERT INTO log_referral_requests (referral_request_id, changetype) VALUES(Old.id, TG_OP);
                        END IF;
                        RETURN NEW;
                    END;
                    $log_request_trg$
                    LANGUAGE plpgsql;
            """
            engine.execute(log_trigger_function)

            log_trigger = """
                CREATE TRIGGER log_request_trg AFTER INSERT OR UPDATE OR DELETE ON referral_requests
                FOR EACH ROW execute Procedure log_request();
            """
            engine.execute(log_trigger)
        else:
            print("Trigger to record referral_request log already exists....................................")

        #----------------  Roles Table  --------------------#

        if not engine.dialect.has_table(connection, "roles"):

            print("Creating roles Table..........................................")

            roles = Table(
                "roles", meta,
                Column("id", Integer, primary_key = True),
                Column("role", String(255)),
                Column("name", String(255)),
                Column("is_provider", Boolean, server_default = "0"),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now()),
                UniqueConstraint("role")
            )
            meta.create_all(engine)

            role_updated_trigger = '''
                CREATE TRIGGER set_role_updated_at
                BEFORE UPDATE ON roles
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(role_updated_trigger)

            # insert_roles = role_table.insert().values(
            #     [
            #         {"name" : "Super Administrator", "role" : "Super Administrator", "is_provider" : False},
            #         {"name" : "Administrator", "role" : "Administrator", "is_provider" : False},
            #         {"name" : "Account Administrator", "role" : "Account Administrator", "is_provider" : False},
            #         {"name" : "Organization Authorized Personnel", "role" : "Organization Authorized Personnel", "is_provider" : False},
            #         {"name" : "Organization Administrator", "role" : "Organization Administrator", "is_provider" : False},
            #         {"name" : "Therapist", "role" : "Therapist", "is_provider" : True},
            #         {"name" : "Teacher", "role" : "Teacher", "is_provider" : False},
            #         {"name" : "Client", "role" : "Client", "is_provider" : False},
            #         {"name" : "Nurse Practitioner", "role" : "Nurse Practitioner", "is_provider" : True},
            #         {"name" : "Classroom", "role" : "Classroom", "is_provider" : False}
            #     ]
            # )
            # connection.execute(insert_roles)
        else:
            print("Table roles already exists.........................................")

        #------------------- Users Table ---------------------#

        if not engine.dialect.has_table(connection, "users"):
            role_table = Table(
                'roles',
                meta,
                autoload=True,
                autoload_with=engine
            )

            print("Creating users table.................................................")

            users = Table(
                        "users", meta,
                        Column("id", Integer, primary_key = True),
                        Column("first_name", String(255)),
                        Column("last_name", String(255)),
                        Column("username", String(255)),
                        Column("password", String(255)),
                        Column("email", String(255)),
                        Column("phone", Integer),
                        Column("role_id", Integer, ForeignKey("roles.id"), nullable = False),
                        Column("is_verified", Boolean, server_default = "0"),
                        Column("verification_type", String(255)),
                        Column("verified_at", DateTime(timezone=True)),
                        Column("archived", Boolean, server_default = "0"),
                        Column("created_at", DateTime(timezone=True), server_default=func.now()),
                        Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now()),
                        UniqueConstraint("username"),
                        UniqueConstraint("email"),
                    )

            meta.create_all(engine)

            user_updated_trigger = '''
                CREATE TRIGGER set_user_updated_at
                BEFORE UPDATE ON users
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(user_updated_trigger)
        else:
            print("Table users already exists...................................................")

        #---- Adding Column to store reset password token ----#
        add_column = "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token VARCHAR(255)"
        engine.execute(add_column)
        print("Column password_reset_token updated successfully.....................")

        #---- Permissions Table ----#
        if not engine.dialect.has_table(connection, "permissions"):
            print("Creating permissions table...........................")
            permissions = Table(
                "permissions", meta,
                Column("id", Integer, primary_key = True),
                Column("category", String(255)),
                Column("level", String(255)),
                Column("display_name", String(255)),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now()),
                UniqueConstraint("display_name")
            )

            meta.create_all(engine)

            permission_updated_trigger = '''
                CREATE TRIGGER set_permission_updated_at
                BEFORE UPDATE ON permissions
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(permission_updated_trigger)
        else:
            print("Table permissions already exists.....................")

        #---- Default Role Permissions Table ----#
        if not engine.dialect.has_table(connection, "default_role_permissions"):
            print("Creating default_role_permissions table...........................")

            role_table = Table(
                'roles',
                meta,
                autoload = True,
                autoload_with = engine
            )

            permission_table = Table(
                'permissions',
                meta,
                autoload = True,
                autoload_with = engine
            )

            default_role_permissions = Table(
                "default_role_permissions", meta,
                Column("id", Integer, primary_key = True),
                Column("role_id", Integer, ForeignKey("roles.id"), nullable = False),
                Column("permission_id", Integer, ForeignKey("permissions.id"), nullable = False),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
            )

            meta.create_all(engine)

            role_permission_updated_trigger = '''
                CREATE TRIGGER set_role_permission_updated_at
                BEFORE UPDATE ON default_role_permissions
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(role_permission_updated_trigger)
        else:
            print("Table default_role_permissions already exists.....................")

        #---- User Permissions Table ----#
        if not engine.dialect.has_table(connection, "user_permissions"):
            print("Creating user_permissions table...........................")

            user_table = Table(
                'users',
                meta,
                autoload = True,
                autoload_with = engine
            )

            permission_table = Table(
                'permissions',
                meta,
                autoload = True,
                autoload_with = engine
            )

            user_permissions = Table(
                "user_permissions", meta,
                Column("id", Integer, primary_key = True),
                Column("user_id", Integer, ForeignKey("users.id"), nullable = False),
                Column("permission_id", Integer, ForeignKey("permissions.id"), nullable = False),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
            )

            meta.create_all(engine)

            user_permission_updated_trigger = '''
                CREATE TRIGGER set_user_permission_updated_at
                BEFORE UPDATE ON user_permissions
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(user_permission_updated_trigger)
        else:
            print("Table user_permissions already exists.....................")

        #---- Adding Column Description In Permissions Table ----#
        add_column = "ALTER TABLE permissions ADD COLUMN IF NOT EXISTS description TEXT"
        engine.execute(add_column)
        print("Column description updated successfully.....................")

        #---- Adding Column is_master In Users Table ----#
        add_column = "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_master BOOLEAN NOT NULL default '0'"
        engine.execute(add_column)
        print("Column is_master updated successfully.....................")

        #---- Adding Column role_level In Roles Table ----#
        if "unique_levl" not in [constraint["name"] for constraint in engine.dialect.get_unique_constraints(connection, "roles")]:
            add_column = "ALTER TABLE roles ADD COLUMN IF NOT EXISTS role_level INTEGER, ADD CONSTRAINT unique_levl UNIQUE (role_level);"
            engine.execute(add_column)
            print("Column role_level updated successfully.....................")

        #---- Create Table to Log Error Details ----#
        if not engine.dialect.has_table(connection, "request_error_details"):
            print("Creating request_error_details table...........................")

            ref_requests = Table(
                "referral_requests",
                meta,
                autoload = True,
                autoload_with = engine
            )

            request_error_details = Table(
                "request_error_details", meta,
                Column("id", Integer, primary_key = True),
                Column("request_id", Integer, ForeignKey("referral_requests.id")),
                Column("url", String(255)),
                Column("payload", JSON),
                Column("error_type", String(255)),
                Column("error_details", Text),
                Column("error_reason", Text),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
            )

            meta.create_all(engine)

            request_error_updated_trigger = '''
                CREATE TRIGGER set_request_error_updated_at
                BEFORE UPDATE ON request_error_details
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(request_error_updated_trigger)
        else:
            print("Table request_error_details already exists.....................")

        #---- Adding Column note In Permissions Table ----#
        add_column = "ALTER TABLE referral_requests ADD COLUMN IF NOT EXISTS note TEXT"
        engine.execute(add_column)
        print("Column note updated successfully.....................")

        #---- Adding Column archived In request_error_details Table ----#
        add_column = "ALTER TABLE request_error_details ADD COLUMN IF NOT EXISTS archived BOOLEAN NOT NULL default '0'"
        engine.execute(add_column)
        print("Column archived updated successfully.....................")

        #---- Default Organizations Table ----#
        if not engine.dialect.has_table(connection, "organizations"):
            print("Creating organizations table...........................")
            organizations = Table(
                "organizations", meta,
                Column("id", Integer, primary_key = True),
                Column("abbr", String(255)),
                Column("subdomain", String(255)),
                Column("archived", Boolean, server_default = "0"),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now()),
                UniqueConstraint("abbr"),
                UniqueConstraint("subdomain")
            )
            meta.create_all(engine)

            organizations_updated_trigger = '''
                CREATE TRIGGER set_organizations_updated_at
                BEFORE UPDATE ON organizations
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(organizations_updated_trigger)
        else:
            print("Table organizations already exists.....................")

        #---- Create Table Organization Contacts Details ----#
        if not engine.dialect.has_table(connection, "organization_contacts"):
            print("Creating organization_contacts table...........................")

            organizations = Table(
                "organizations",
                meta,
                autoload = True,
                autoload_with = engine
            )

            organization_contacts = Table(
                "organization_contacts", meta,
                Column("id", Integer, primary_key = True),
                Column("organization_id", Integer, ForeignKey("organizations.id")),
                Column("contact_person", String(255)),
                Column("phone", String(255)),
                Column("mobile", String(255)),
                Column("email", String(255)),
                Column("archived", Boolean, server_default = "0"),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
            )
            meta.create_all(engine)

            organization_contacts_updated_trigger = '''
                CREATE TRIGGER set_organization_contacts_updated_at
                BEFORE UPDATE ON organization_contacts
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(organization_contacts_updated_trigger)
        else:
            print("Table organization_contacts already exists.....................")

        #---- Create Table referral_token ----#
        if not engine.dialect.has_table(connection, "referral_tokens"):
            print("Creating referral_tokens table...........................")

            organizations = Table(
                "organizations",
                meta,
                autoload = True,
                autoload_with = engine
            )

            referral_tokens = Table(
                "referral_tokens", meta,
                Column("id", Integer, primary_key = True),
                Column("organization_id", Integer, ForeignKey("organizations.id")),
                Column("token", Text),
                Column("expiry_date", DateTime(timezone=True)),
                Column("archived", Boolean, server_default = "0"),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
            )
            meta.create_all(engine)

            referral_tokens_updated_trigger = '''
                CREATE TRIGGER set_referral_tokens_updated_at
                BEFORE UPDATE ON referral_tokens
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(referral_tokens_updated_trigger)
        else:
            print("Table referral_tokens already exists.....................")


        #---- Create Table documentation_token ----#
        if not engine.dialect.has_table(connection, "documentation_tokens"):
            print("Creating documentation_tokens table...........................")

            organizations = Table(
                "organizations",
                meta,
                autoload = True,
                autoload_with = engine
            )

            documentation_tokens = Table(
                "documentation_tokens", meta,
                Column("id", Integer, primary_key = True),
                Column("organization_id", Integer, ForeignKey("organizations.id"), nullable = True),
                Column("token", Text),
                Column("expiry_date", DateTime(timezone=True)),
                Column("archived", Boolean, server_default = "0"),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
            )
            meta.create_all(engine)

            documentation_tokens_updated_trigger = '''
                CREATE TRIGGER set_documentation_tokens_updated_at
                BEFORE UPDATE ON documentation_tokens
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(documentation_tokens_updated_trigger)
        else:
            print("Table documentation_tokens already exists.....................")

        #---- Create Table organization_amd_codes ----#
        if not engine.dialect.has_table(connection, "organization_amd_codes"):
            print("Creating organization_amd_codes table...........................")

            organizations = Table(
                "organizations",
                meta,
                autoload = True,
                autoload_with = engine
            )

            organization_amd_codes = Table(
                "organization_amd_codes", meta,
                Column("id", Integer, primary_key = True),
                Column("organization_id", Integer, ForeignKey("organizations.id")),
                Column("financial_class", String(255)),
                Column("referral_provider_code", String(255)),
                Column("default_referral_status", String(255)),
                Column("archived", Boolean, server_default = "0"),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
            )
            meta.create_all(engine)

            organization_amd_codes_updated_trigger = '''
                CREATE TRIGGER set_organization_amd_codes_updated_at
                BEFORE UPDATE ON organization_amd_codes
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(organization_amd_codes_updated_trigger)
        else:
            print("Table organization_amd_codes already exists.....................")

        add_column = "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS title VARCHAR(255)"
        add_column = "ALTER TABLE organizations ADD COLUMN IF NOT EXISTS assets JSON"
        engine.execute(add_column)

        if not engine.dialect.has_table(connection, "referral_request_notes"):
            print("Creating referral_request_notes table...........................")

            referral_requests_table = get_table("referral_requests", meta, engine)
            users_table = get_table("users", meta, engine)

            referral_request_notes = Table(
                "referral_request_notes", meta,
                Column("id", Integer, primary_key = True),
                Column("referral_request_id", Integer, ForeignKey("referral_requests.id")),
                Column("note", Text),
                Column("added_by", Integer, ForeignKey("users.id")),
                Column("archived", Boolean, server_default = "0"),
                Column("created_at", DateTime(timezone=True), server_default=func.now()),
                Column("updated_at", DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
            )
            meta.create_all(engine)

            referral_request_notes_updated_trigger = '''
                CREATE TRIGGER set_referral_request_notes_updated_at
                BEFORE UPDATE ON referral_request_notes
                FOR EACH ROW
                EXECUTE PROCEDURE trigger_set_timestamp();
            '''
            connection.execute(referral_request_notes_updated_trigger)
        else:
            print("Table referral_requests_notes already exists.....................")


        return {"status_code": 200, "msg": "Changes migrated successfully"}
