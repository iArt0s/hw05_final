from django.core.paginator import Paginator

PAGINATOR_COUNT = 10
MAX_CHAR_LENGTH = 15


def pagination(queryset, request):
    paginator = Paginator(queryset, PAGINATOR_COUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return {'page_obj': page_obj}
