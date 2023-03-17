from nuremberg.core.highlighter import NurembergHighlighter


def test_html_tag():
    h = NurembergHighlighter(query='')

    assert h.html_tag == 'mark'


def test_query_words():
    h = NurembergHighlighter(query='  foo   bar "exact phrase"  non-exact ')

    assert sorted(h.query_words) == ['bar', 'exact phrase', 'foo', 'non-exact']
