import xml.etree.ElementTree

import lxml.etree
import pytest

from xml2db import DataModel
from .sample_models import models


@pytest.mark.parametrize(
    "args",
    [
        ("invalid", True, False, ValueError),
        ("invalid", True, True, ValueError),
        ("invalid", False, False, ValueError),
        ("invalid", False, True, ValueError),
        ("malformed_recover", True, False, lxml.etree.XMLSyntaxError),
        ("malformed_recover", True, True, None),
        ("malformed_recover", False, False, lxml.etree.XMLSyntaxError),
        ("malformed_recover", False, True, None),
        ("malformed_no_recover", True, False, lxml.etree.XMLSyntaxError),
        ("malformed_no_recover", True, True, ValueError),
        ("malformed_no_recover", False, False, lxml.etree.XMLSyntaxError),
        ("malformed_no_recover", False, True, ValueError),
    ],
)
def test_invalid_xml(args: tuple):

    file_name, iterparse, recover, exception = args
    data_model = DataModel(models[0]["xsd_path"])

    if exception is None:
        data_model.parse_xml(
            f"tests/sample_models/orders/invalid_xml/{file_name}.xml",
            skip_validation=False,
            iterparse=iterparse,
            recover=recover,
        )
    else:
        with pytest.raises(exception):
            data_model.parse_xml(
                f"tests/sample_models/orders/invalid_xml/{file_name}.xml",
                skip_validation=False,
                iterparse=iterparse,
                recover=recover,
            )


@pytest.mark.parametrize(
    "args",
    [
        ("invalid", True, False, IndexError),
        ("invalid", True, True, IndexError),
        ("invalid", False, False, None),
        ("invalid", False, True, None),
        ("malformed_recover", True, False, lxml.etree.XMLSyntaxError),
        ("malformed_recover", True, True, None),
        ("malformed_recover", False, False, lxml.etree.XMLSyntaxError),
        ("malformed_recover", False, True, None),
        ("malformed_no_recover", True, False, lxml.etree.XMLSyntaxError),
        ("malformed_no_recover", True, True, IndexError),
        ("malformed_no_recover", False, False, lxml.etree.XMLSyntaxError),
        ("malformed_no_recover", False, True, None),
    ],
)
def test_invalid_xml_skip_verify(args: tuple):

    file_name, iterparse, recover, exception = args
    data_model = DataModel(models[0]["xsd_path"])

    if exception is None:
        data_model.parse_xml(
            f"tests/sample_models/orders/invalid_xml/{file_name}.xml",
            skip_validation=True,
            iterparse=iterparse,
            recover=recover,
        )
    else:
        with pytest.raises(exception):
            data_model.parse_xml(
                f"tests/sample_models/orders/invalid_xml/{file_name}.xml",
                skip_validation=True,
                iterparse=iterparse,
                recover=recover,
            )
