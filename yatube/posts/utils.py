from django.core.paginator import Paginator
from .constants import PAGINATOR_COUNT


def pagination(queryset, request):
    """функция пагинатора"""
    paginator = Paginator(queryset, PAGINATOR_COUNT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return {'page_obj': page_obj}
