import pytest
from django.db.models import Max
from model_bakery import baker

from nuremberg.documents.models import PersonalAuthorProperty


@pytest.mark.django_db
def make_author(**kwargs):
    # ensure baked authors have an ID higher than the current MAX author ID
    # in the properties table
    max_id = PersonalAuthorProperty.objects.aggregate(
        max_author_id=Max('personal_author_id')
    )['max_author_id']
    return baker.make('DocumentPersonalAuthor', id=max_id + 10, **kwargs)
