# django-rest-framework
# doc: https://www.django-rest-framework.org/

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'tone.core.common.pagination.StandardResultPagination',
    'EXCEPTION_HANDLER': 'tone.core.common.exceptions.exception_handler.common_exception_handler',
}

# django-cors-headers setting
CORS_ORIGIN_ALLOW_ALL = True
