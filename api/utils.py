from manhattan.forms import BaseForm, fields, validators, utils as form_utils
from mongoframes import And, Q, SortBy
from werkzeug.datastructures import MultiDict
from werkzeug.urls import url_encode

__init__ = [

    # Classes
    'PaginationForm'

    # Functions
    'paginate',
    'to_multi_dict'
]


# Classes

class PaginationForm(BaseForm):

    after = fields.HiddenField(coerce=form_utils.to_object_id)

    before = fields.HiddenField(coerce=form_utils.to_object_id)

    limit = fields.IntegerField(
        'Limit',
        validators=[validators.NumberRange(1, 100)],
        default=10
    )


# Functions

def paginate(
    collection,
    query_stack,
    request,
    before=None,
    after=None,
    limit=10,
    projection=None
):
    """
    Return a page of documents from the given collection as a pagination
    response.
    """

    query_stack = list(query_stack)
    paginated_query_stack = list(query_stack)

    # Apply offset
    if before:
        paginated_query_stack.append(Q._id < before)

    elif after:
        paginated_query_stack.append(Q._id > after)

    # Get the page of results
    results = collection.many(
        And(*paginated_query_stack),
        sort=SortBy(Q._id),
        limit=limit,
        projection=projection
    )

    # Count the total results available
    count = collection.count(And(*query_stack))

    # Determine if there are more results to fetch
    remaining_count = collection.count(And(*paginated_query_stack)) - limit
    has_more = remaining_count > 0

    # Build the URL
    args = to_multi_dict(request.query_arguments)
    for key, value in list(args.items()):
        if not value:
            args.pop(key)

        if key in ['after', 'before', 'limit']:
            args.pop(key)

    url = '{0}{1}'.format(
        request.uri.split('?', 1)[0],
        '?' + url_encode(args) if args else ''
    )

    return {
        'has_more': has_more,
        'result_count': count,
        'results': [r.to_json_type() for r in results],
        'url': url
    }

def to_multi_dict(arguments):
    """
    Convert a dictionary of the form provided by `request.arguments` into a
    `MultiDict` structure suitable for use with forms.
    """

    pairs = []
    for key, values in arguments.items():
        pairs.extend([(key, v.decode('utf8')) for v in values])

    return MultiDict(pairs)
