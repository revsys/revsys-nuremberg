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


def test_bug_repro():
    response = client.get('')

    error = response.context['session'].get('a-key')
    assert error is None
