import re

from haystack.utils import Highlighter


EXACT_PHRASE_RE = re.compile(r'"([^"]*)"|([^"]*)')


class NurembergHighlighter(Highlighter):
    def __init__(self, query, **kwargs):
        kwargs.setdefault('html_tag', 'mark')
        super().__init__(query, **kwargs)

        # Extract all exact phrases and treat them as "a single word"
        matches = EXACT_PHRASE_RE.findall(query)
        exact_phrases, non_exact = list(zip(*matches))
        self.query_words = {
            phrase.strip().lower()
            for phrase in exact_phrases
            if phrase.strip()
        }
        self.query_words.update(
            {
                word.strip().lower()
                for item in non_exact
                for word in item.split()
                if item and not word.startswith("-")
            }
        )

    def find_window(self, highlight_locations):
        # Do not truncate the text at all -- show everything, from start to end
        return (0, len(self.text_block))

    def highlight(self, text_block):
        # Override from parent to avoid stripping HTML tags, the original code
        # would do: self.text_block = strip_tags(text_block)
        self.text_block = text_block
        highlight_locations = self.find_highlightable_words()
        start_offset, end_offset = self.find_window(highlight_locations)
        return self.render_html(highlight_locations, start_offset, end_offset)
