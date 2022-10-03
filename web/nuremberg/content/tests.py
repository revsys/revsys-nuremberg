import pytest
from django.urls import reverse

from nuremberg.core.tests.acceptance_helpers import (
    PyQuery,
    client,
)


@pytest.mark.django_db
def test_landing_page():
    response = client.get('/')
    page = PyQuery(response.content)
    assert "Nuremberg" in page('h1').text()

    def link_should_exist(name):
        assert page('a[href="{}"]'.format(reverse(name)))

    link_should_exist('content:trials')
    link_should_exist('content:about')

    search_form = page('form[action="{}"]'.format(reverse('search:search')))
    assert search_form
    assert search_form.find('input[type="search"]')
