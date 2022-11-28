import pytest
from model_bakery import baker

from nuremberg.documents.models import Document, PersonalAuthorProperty


@pytest.mark.django_db
def make_author(**kwargs):
    # ensure baked authors have an ID higher than the current MAX author ID
    # in the properties table
    max_id = (
        PersonalAuthorProperty.objects.all()
        .order_by('personal_author_id')
        .last()
        .id
    )
    return baker.make('DocumentPersonalAuthor', id=max_id + 10, **kwargs)


def make_document(evidence_codes=None, **kwargs):
    max_id = Document.objects.all().order_by('id').last().id
    result = baker.make('Document', id=max_id, **kwargs)

    db_evidence_codes = []
    for code in evidence_codes or []:
        prefix, number = code.split('-', 1)
        db_evidence_codes.append(
            baker.make(
                'DocumentEvidenceCode',
                prefix__code=prefix,
                number=number,
                document=result,
            )
        )

    return result


def make_random_text(length=100):
    base = (
        'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam '
        'sagittis dolor et nisl mattis, at rutrum enim faucibus. Suspendisse '
        'malesuada eros ligula, non hendrerit velit gravida et.'
    )
    result = base * ((len(base) // length) + 1)
    return result[:length]
