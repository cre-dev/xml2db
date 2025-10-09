import os

import pytest

from xml2db import DataModel

models_path = "tests/sample_models"


def list_xml_path(test_config, key):
    path = os.path.join(models_path, test_config["id"], key)
    if os.path.isdir(path):
        return [os.path.join(path, f) for f in os.listdir(path)]
    return []


@pytest.fixture
def conn_string():
    return os.getenv("DB_STRING")


@pytest.fixture(scope="function")
def setup_db_model(conn_string, model_config):
    db_schema = f"test_xml2db"
    model = DataModel(
        xsd_file=str(
            os.path.join(models_path, model_config["id"], model_config["xsd"])
        ),
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
