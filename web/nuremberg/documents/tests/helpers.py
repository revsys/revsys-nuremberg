import pytest
from model_bakery import baker

from nuremberg.documents.models import (
    EVIDENCE_CODE_RE,
    Document,
    DocumentExternalMetadata,
    DocumentText,
    PersonalAuthorProperty,
)


class DummyMemDictStorage:
    """A dummy and silly memory dict-based minimal storage."""

    def __init__(self):
        super().__init__()
        self._paths = {}

    def delete(self, path):
        self._paths.pop(path)

    def exists(self, path):
        return path in self._paths

    def open(self, path):
        return self._paths[path]

    def save(self, path, content):
        self._paths[path] = content


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
    next_id = Document.objects.all().order_by('id').last().id + 1
    print(baker.make('Document', id=next_id).id)
    result = baker.make('Document', id=next_id, **kwargs)
    assert result.id == next_id

    if evidence_codes is None:
        evidence_codes = []
    for code in evidence_codes:
        re_match = EVIDENCE_CODE_RE.match(code)
        assert re_match is not None
        prefix, number, suffix = re_match.groups()
        baker.make(
            'DocumentEvidenceCode',
            prefix__code=prefix,
            number=number,
            suffix=suffix,
            document=result,
        )

    assert sorted(str(e) for e in result.evidence_codes.all()) == sorted(
        evidence_codes
    )
    return result


def make_document_text(evidence_code=None, **kwargs):
    next_id = DocumentText.objects.all().order_by('id').last().id + 1
    if evidence_code is not None:
        re_match = EVIDENCE_CODE_RE.match(evidence_code)
        assert re_match is not None
        prefix, number, _ = re_match.groups()
        # So far the agreement is that DocumentText does not include suffixes,
        # so code PS-343 would match all three PS-343, PS-343a and PS-343b
        kwargs.setdefault('evidence_code_series', prefix)
        kwargs.setdefault('evidence_code_num', number)
    result = baker.make('DocumentText', id=next_id, **kwargs)
    assert result.id == next_id

    return result


def make_document_external_metadata(evidence_code=None, **kwargs):
    next_id = (
        DocumentExternalMetadata.objects.all().order_by('id').last().id + 1
    )
    if evidence_code is not None:
        re_match = EVIDENCE_CODE_RE.match(evidence_code)
        assert re_match is not None
        prefix, number, suffix = re_match.groups()
        kwargs.setdefault('evidence_code_series', prefix)
        kwargs.setdefault('evidence_code_num', number)
        kwargs.setdefault('evidence_code_suffix', suffix)
    result = baker.make('DocumentExternalMetadata', id=next_id, **kwargs)
    assert result.id == next_id

    return result


def make_random_text(length=100):
    base = (
        'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nullam '
        'sagittis dolor et nisl mattis, at rutrum enim faucibus. Suspendisse '
        'malesuada eros ligula, non hendrerit velit gravida et.'
    )
    result = base * ((len(base) // length) + 1)
    return result[:length]
