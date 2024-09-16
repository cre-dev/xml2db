import os

import pytest

from xml2db import DataModel


@pytest.fixture
def conn_string():
    return os.getenv("DB_STRING")


@pytest.fixture(scope="function")
def setup_db_model(conn_string, model_config):
    db_schema = f"test_xml2db"
    model = DataModel(
        xsd_file=model_config.get("xsd_path"),
        short_name=model_config.get("id"),
        connection_string=conn_string,
        db_schema=db_schema,
        model_config=model_config.get("config"),
    )
    model.create_db_schema()
    model.drop_all_tables()
    model.create_all_tables(temp=False)

    yield model

    model.drop_all_tables()
