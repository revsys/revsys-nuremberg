from nuremberg.documents.templatetags.author_properties import qualifierformat


def test_qualifierformat_no_changes():
    original = [
        ('work location', ['Some County', 'Other Place']),
        ('until', ['1919-01-01']),
        ('since', ['1928-07-01']),
        ('house number', ['16']),
    ]

    result = qualifierformat(original)

    assert result == '; '.join(f'{q}: {", ".join(qs)}' for q, qs in original)


def test_qualifierformat_period_date_list():
    periods = [
        ('1927-03-04', '1929-03-04'),
        ('1929-03-04', '1931-03-04'),
        ('1931-03-04', '1933-03-04'),
        ('1933-03-04', '1935-01-03'),
        ('1935-01-03', '1937-01-03'),
        ('1937-01-03', '1939-01-03'),
        ('1939-01-03', '1941-01-03'),
        ('1941-01-03', '1943-01-03'),
        ('1943-01-03', '1945-01-03'),
        ('1945-01-03', '1947-01-03'),
        ('1947-01-03', '1949-01-03'),
        ('1949-01-03', '1949-01-19'),
        ('1955-01-03', '1956-04-30'),
    ]

    result = qualifierformat([('period', periods)])

    assert result == 'period: ' + ', '.join(
        ' through '.join(i) for i in periods
    )


def test_qualifierformat_max_qualifiers():
    original = [
        (f'q{i}', [f'val{i}{j}' for j in range(1, i + 1)]) for i in range(1, 6)
    ]

    result = qualifierformat(original, max_qualifiers=None)
    assert result == '; '.join(f'{q}: {", ".join(qs)}' for q, qs in original)

    result = qualifierformat(original, max_qualifiers=10)
    assert result == '; '.join(f'{q}: {", ".join(qs)}' for q, qs in original)

    result = qualifierformat(original, max_qualifiers=3)
    expected = [
        ('q1', ['val11']),
        ('q2', ['val21', 'val22']),
        ('q3', ['val31', 'val32', 'val33']),
    ]
    assert result == '; '.join(f'{q}: {", ".join(qs)}' for q, qs in expected)


def test_qualifierformat_max_qualifier_values():
    original = [('something', ['val1', 'val2', 'val3', 'val4'])]

    result = qualifierformat(original, max_qualifier_values=None)
    assert result == 'something: val1, val2, val3, val4'

    result = qualifierformat(original, max_qualifier_values=10)
    assert result == 'something: val1, val2, val3, val4'

    result = qualifierformat(original, max_qualifier_values=3)
    assert result == 'something: val1, val2, ..., val4'

    result = qualifierformat(original, max_qualifier_values=2)
    assert result == 'something: val1, ..., val4'

    result = qualifierformat(original, max_qualifier_values=1)
    assert result == 'something: val1, ...'

    result = qualifierformat([('something', ['val1'])], max_qualifier_values=1)
    assert result == 'something: val1'
