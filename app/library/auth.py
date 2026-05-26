import requests
import jwt
from django.conf import settings
from django.http import JsonResponse
from .models import ReaderUser

JWKS_CACHE = None


def get_jwks():
    global JWKS_CACHE
    if JWKS_CACHE is None:
        if not settings.SUPABASE_JWKS_URL:
            raise RuntimeError('SUPABASE_JWKS_URL is not configured')
        JWKS_CACHE = requests.get(settings.SUPABASE_JWKS_URL, timeout=10).json()
    return JWKS_CACHE


def verify_supabase_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    jwks = get_jwks()
    jwk = next((k for k in jwks.get('keys', []) if k.get('kid') == header.get('kid')), None)
    if not jwk:
        raise ValueError('No matching signing key found')
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
    return jwt.decode(token, public_key, algorithms=['RS256'], options={'verify_aud': False})


def auth_error(message: str, status: int = 401):
    return JsonResponse({'detail': message}, status=status)


def get_user_from_request(request):
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ', 1)[1]
    claims = verify_supabase_token(token)
    user_id = claims.get('sub')
    if not user_id:
        raise ValueError('Missing user id in token')
    user, _ = ReaderUser.objects.get_or_create(
        supabase_user_id=user_id,
        defaults={'email': claims.get('email', '') or ''},
    )
    email = claims.get('email', '') or ''
    if email and user.email != email:
        user.email = email
        user.save(update_fields=['email'])
    return user
