from nuremberg.core.highlighter import NurembergHighlighter


def test_html_tag():
    h = NurembergHighlighter(query='')

    assert h.html_tag == 'mark'


def test_query_words():
    h = NurembergHighlighter(query='  foo   bar "exact phrase"  non-exact ')

    assert sorted(h.query_words) == ['bar', 'exact phrase', 'foo', 'non-exact']


def test_query_words_search_terms():
    h = NurembergHighlighter(query='  foo evidence:PS-62 "exact phrase"  bar ')

    assert sorted(h.query_words) == ['bar', 'exact phrase', 'foo', 'ps-62']


def test_highlight_skips_html_tags():
    # Mimics real case for
    # /transcripts/4?seq=351&q=german+evidence:NOKW-192+LATERNSER+speaker
    h = NurembergHighlighter(
        query='german evidence:NOKW-192 LATERNSER speaker'
    )

    assert sorted(h.query_words) == [
        'german',
        'laternser',
        'nokw-192',
        'speaker',
    ]

    text = (
        '<p>'
        'If your Honors please, we turn now to the early days of October in '
        'the Southeast, particularly Serbia. The first document which is at '
        'page one of that book, and also page one of the German is '
        '<a href="/search?q=evidence%3A%22NOKW-192%22">NOKW-192</a> which we '
        'offer as Exhibit 78.'
        '</p>'
        '<p>'
        '<span class="speaker">DR. LATERNSER:</span>  Your honors, I object '
        'to the submission of this document because it is not signed.'
        '</p>'
    )
    expected = (
        '<p>'
        'If your Honors please, we turn now to the early days of October in '
        'the Southeast, particularly Serbia. The first document which is at '
        'page one of that book, and also page one of the '
        '<mark class="highlighted">German</mark> is '
        '<a href="/search?q=evidence%3A%22NOKW-192%22">'
        '<mark class="highlighted">NOKW-192</mark></a> '
        'which we offer as Exhibit 78.'
        '</p>'
        '<p>'
        '<span class="speaker">DR. <mark class="highlighted">LATERNSER</mark>:'
        '</span>  Your honors, I object to the submission of this document '
        'because it is not signed.'
        '</p>'
    )
    actual = h.highlight(text)
    assert actual == expected


def test_highlight_skips_html_tags_multiple_locations():
    # Mimics real case for
    # /transcripts/7?seq=4012&q=trial:imt+type:transcript+January+speaker
    h = NurembergHighlighter(query='trial:imt type:transcript January speaker')

    assert sorted(h.query_words) == [
        'imt',
        'january',
        'speaker',
        'transcript',
    ]

    text = (
        '<p>'
        '<span class="speaker">THE PRESIDENT:</span>   It would help us, I '
        'think, when you are passing on in your expose, if you were to say '
        'that you were passing to such and such a page. We should then be '
        'able to go on with it.'
        '</p>'
        '<p>'
        'Will you do that?'
        '</p>'
        '<p>'
        '<span class="speaker">M. GERTHOFFER:</span>   Yes.  This is page 14 '
        'of the brief.  It is a copy of a document which was discovered by '
        'the American Army, which bears the number 1-PS, which I offer in '
        'evidence in the form of a copy in the Document Book under the number '
        '1311.'
        '</p>'
    )
    expected = text  # no highlight

    actual = h.highlight(text)
    assert actual == expected
