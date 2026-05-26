from .auth import get_user_from_request


class SupabaseAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.reader_user = None
        try:
            request.reader_user = get_user_from_request(request)
        except Exception:
            request.reader_user = None
        return self.get_response(request)
