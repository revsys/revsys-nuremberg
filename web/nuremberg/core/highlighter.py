import re

from haystack.utils import Highlighter


EXACT_PHRASE_RE = re.compile(r'"([^"]*)"|([^"]*)')
FIELD_SEARCH_RE = re.compile(r'[a-zA-Z0-9_-]+:([^:]*)')


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
        # Extract special search terms from non exact terms, if any
        self.query_words.update(
            {
                w
                for item in non_exact
                for word in item.split()
                for w in self.process_word(word)
                if item and not word.startswith("-")
            }
        )

    def process_word(self, word):
        # If `query` contains special search syntax like "type:transcript" or
        # "evidence:NOKW-192", the following will drop "type:" or "evidence:"
        # and will highlight "transcript" and "NOKW-192" if present in the text
        word = word.strip().lower()
        matches = FIELD_SEARCH_RE.findall(word)
        if matches:
            result = matches
        else:
            result = [word]
        return result

    def find_window(self, highlight_locations):
        # Do not truncate the text at all -- show everything, from start to end
        return (0, len(self.text_block))

    def highlight(self, text_block):
        # Override from parent to avoid stripping HTML tags, the original code
        # would do: self.text_block = strip_tags(text_block).
        self.text_block = text_block

        # This call matches the parent implementation.
        highlight_locations = self.find_highlightable_words()

        # NEW: given that we haven't strippped HTML tags, we need to discard
        # those values from `highlight_locations` that are within an HTML tag
        # (i.e. word matches that are tag attributes, such as CSS classes and
        #  hrefs pointing to search terms, see the below for an example).
        # The following is a naive heuristic that may need improvement in a
        # future iteration, perhaps using HTMLParser.
        # Example of this is:
        # /transcripts/4?seq=351&q=german+evidence:NOKW-192+LATERNSER+speaker
        # `speaker` is a CSS class used to format trial speaker names, and
        # `NOKW-192` is part of a href link to search for all the items
        # referencing that evidence code.
        for word, locations in highlight_locations.items():
            for location in list(locations):  # copy to allow for modification
                # is this location inside an opened HTML tag?
                tags = [i for i in text_block[location:] if i in ['>', '<']]
                if tags and tags[0] == '>':
                    locations.remove(location)

        # These two last calls match the parent implementation.
        start_offset, end_offset = self.find_window(highlight_locations)
        return self.render_html(highlight_locations, start_offset, end_offset)
