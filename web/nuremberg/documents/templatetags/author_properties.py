from django import template
from django.utils.translation import gettext as _


register = template.Library()


@register.simple_tag
def qualifierformat(
    qualifiers, max_qualifiers=None, max_qualifier_values=None
):
    """Format a property's qualifiers.

    The merging of properties and qualifiers should display property followed
    by the qualifier in parentheses:

        "property: property value (qualifier1: qualifier value)"

    e.g., "participant in: Nuremberg Medical Trial (role: prosecutor)"

    Multiple qualifiers are separated by a semicolon, while multiple qualifier
    values are separated by a comma.

    For the qualifiers "start time" and "end time" for some property, on the
    front end, we'd like to simply see a parenthesized expression with the two
    dates separated by "through": "1933-10-15 through 1936-11-01".

    The number of different qualifiers may be limited to `max_qualifiers` in
    order to improve the readability of the information in smaller contexts.

    The amount of qualifier values for a given qualifier may be limited to
    `max_qualifier_values`. If `max_qualifier_values` is 2 or higher,
    the first `max_qualifier_values` - 1 and the last will be used with a
    joining ellipsis.

    """
    result = []
    for q, qs in qualifiers[:max_qualifiers]:
        if q == 'period':
            qs = [
                _(f'{start_date} through {end_date}')
                for start_date, end_date in qs
            ]

        if max_qualifier_values and len(qs) > max_qualifier_values:
            *rest, last = qs
            if max_qualifier_values > 1:
                # Pick the first N-1 and the last qualifier values, and then
                # separate by an ellipsis
                qs = rest[: max_qualifier_values - 1] + ['...', last]
            else:
                qs = [rest[0], '...']

        result.append(f'{q}: {", ".join(qs)}')

    return '; '.join(result)
