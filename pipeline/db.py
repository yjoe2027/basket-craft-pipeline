import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()


def get_mysql_engine():
    url = (
        "mysql+pymysql://{user}:{password}@{host}:{port}/{db}".format(
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASSWORD"],
            host=os.environ["MYSQL_HOST"],
            port=os.environ.get("MYSQL_PORT", "3306"),
            db=os.environ["MYSQL_DB"],
        )
    )
    return create_engine(url)


def get_postgres_engine():
    url = (
        "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}".format(
            user=os.environ["POSTGRES_USER"],
            password=os.environ["POSTGRES_PASSWORD"],
            host=os.environ["POSTGRES_HOST"],
            port=os.environ.get("POSTGRES_PORT", "5432"),
            db=os.environ["POSTGRES_DB"],
        )
    )
    return create_engine(url)


def get_rds_engine():
    url = (
        "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}".format(
            user=os.environ["RDS_USER"],
            password=os.environ["RDS_PASSWORD"],
            host=os.environ["RDS_HOST"],
            port=os.environ.get("RDS_PORT", "5432"),
            db=os.environ["RDS_DATABASE"],
        )
    )
    return create_engine(url)
