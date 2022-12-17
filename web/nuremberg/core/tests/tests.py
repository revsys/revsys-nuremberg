import pytest

from nuremberg.core.tests.acceptance_helpers import (
    PyQuery,
    client,
)


@pytest.mark.django_db
def test_404():
    response = client.get("THIS_URL_DOES_NOT_EXIST")
    page = PyQuery(response.content)

    assert "can't find" in page('h1').text()
