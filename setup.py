from pathlib import Path
import textwrap

ROOT = Path('django-supabase-epub-reader')

FILES = {
    'manage.py': '''#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reader_project.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
''',

    'reader_project/__init__.py': '',

    'reader_project/settings.py': '''from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-secret-key')
DEBUG = os.getenv('DEBUG', 'True') == 'True'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'library',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'library.middleware.SupabaseAuthMiddleware',
]

ROOT_URLCONF = 'reader_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'reader_project.wsgi.application'
ASGI_APPLICATION = 'reader_project.asgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('POSTGRES_DB', 'postgres'),
        'USER': os.getenv('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
        'HOST': os.getenv('POSTGRES_HOST', ''),
        'PORT': os.getenv('POSTGRES_PORT', '5432'),
        'OPTIONS': {'sslmode': os.getenv('POSTGRES_SSLMODE', 'require')},
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'library' / 'static']
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', '')
SUPABASE_JWKS_URL = os.getenv(
    'SUPABASE_JWKS_URL',
    f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else ''
)
''',

    'reader_project/urls.py': '''from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from library import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('app/', views.reader_app, name='reader_app'),
    path('api/books/', views.books_api, name='books_api'),
    path('api/books/<int:book_id>/', views.book_detail_api, name='book_detail_api'),
    path('api/books/<int:book_id>/chapter/', views.book_chapter_api, name='book_chapter_api'),
    path('api/books/<int:book_id>/progress/', views.book_progress_api, name='book_progress_api'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
''',

    'reader_project/asgi.py': '''import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reader_project.settings')
application = get_asgi_application()
''',

    'reader_project/wsgi.py': '''import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reader_project.settings')
application = get_wsgi_application()
''',

    'library/__init__.py': '',

    'library/apps.py': '''from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'library'
''',

    'library/models.py': '''from django.db import models


class ReaderUser(models.Model):
    supabase_user_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email or self.supabase_user_id


class Book(models.Model):
    user = models.ForeignKey(ReaderUser, on_delete=models.CASCADE, related_name='books')
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    epub_file = models.FileField(upload_to='epubs/')
    slug = models.SlugField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ReadingProgress(models.Model):
    user = models.ForeignKey(ReaderUser, on_delete=models.CASCADE, related_name='progress_items')
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name='progress')
    chapter_index = models.PositiveIntegerField(default=0)
    chapter_href = models.CharField(max_length=500, blank=True)
    locator = models.CharField(max_length=255, blank=True)
    percent = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user} · {self.book}'
''',

    'library/admin.py': '''from django.contrib import admin
from .models import ReaderUser, Book, ReadingProgress

admin.site.register(ReaderUser)
admin.site.register(Book)
admin.site.register(ReadingProgress)
''',

    'library/forms.py': '''from django import forms


class UploadBookForm(forms.Form):
    file = forms.FileField()
''',

    'library/auth.py': '''import requests
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
''',

    'library/middleware.py': '''from .auth import get_user_from_request


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
''',

    'library/views.py': '''import json
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .auth import auth_error
from .epub import parse_book, chapter_html
from .forms import UploadBookForm
from .models import Book, ReadingProgress


def home(request):
    return render(request, 'library/index.html', {
        'SUPABASE_URL': settings.SUPABASE_URL,
        'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
    })


def reader_app(request):
    return render(request, 'library/app.html', {
        'SUPABASE_URL': settings.SUPABASE_URL,
        'SUPABASE_ANON_KEY': settings.SUPABASE_ANON_KEY,
    })


def require_reader_user(request):
    user = getattr(request, 'reader_user', None)
    if not user:
        return None, auth_error('Authentication required')
    return user, None


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def books_api(request):
    user, error = require_reader_user(request)
    if error:
        return error

    if request.method == 'GET':
        books = Book.objects.filter(user=user).order_by('title')
        return JsonResponse([
            {
                'id': book.id,
                'title': book.title,
                'author': book.author,
                'progress': book.progress.percent if hasattr(book, 'progress') else 0,
            }
            for book in books
        ], safe=False)

    form = UploadBookForm(request.POST, request.FILES)
    if not form.is_valid():
        return HttpResponseBadRequest('Upload a valid .epub file')

    upload = form.cleaned_data['file']
    if not upload.name.lower().endswith('.epub'):
        return HttpResponseBadRequest('Upload a valid .epub file')

    book = Book.objects.create(
        user=user,
        title='Untitled book',
        author='Unknown author',
        epub_file=upload,
        slug='temp-book',
    )
    meta = parse_book(book.epub_file.path)
    book.title = meta['title']
    book.author = meta['author']
    book.slug = slugify(meta['title']) or f'book-{book.id}'
    book.save()

    ReadingProgress.objects.get_or_create(
        user=user,
        book=book,
        defaults={
            'chapter_index': 0,
            'chapter_href': meta['chapters'][0]['href'] if meta['chapters'] else '',
            'locator': '',
            'percent': 0,
        },
    )
    return JsonResponse({'id': book.id, 'title': book.title, 'author': book.author})


@require_http_methods(['GET'])
def book_detail_api(request, book_id: int):
    user, error = require_reader_user(request)
    if error:
        return error
    book = get_object_or_404(Book, id=book_id, user=user)
    meta = parse_book(book.epub_file.path)
    progress, _ = ReadingProgress.objects.get_or_create(user=user, book=book)
    return JsonResponse({
        'id': book.id,
        'title': book.title,
        'author': book.author,
        'chapters': meta['chapters'],
        'progress': {
            'chapter_index': progress.chapter_index,
            'chapter_href': progress.chapter_href,
            'locator': progress.locator,
            'percent': progress.percent,
        },
    })


@require_http_methods(['GET'])
def book_chapter_api(request, book_id: int):
    user, error = require_reader_user(request)
    if error:
        return error
    book = get_object_or_404(Book, id=book_id, user=user)
    meta = parse_book(book.epub_file.path)
    chapters = meta['chapters']
    if not chapters:
        return HttpResponseBadRequest('This EPUB has no readable spine')
    chapter_index = min(max(int(request.GET.get('chapter', 0)), 0), len(chapters) - 1)
    content = chapter_html(book.epub_file.path, chapters[chapter_index]['href'])
    return JsonResponse({
        'book': {'id': book.id, 'title': book.title, 'author': book.author},
        'chapter_index': chapter_index,
        'chapter': chapters[chapter_index],
        'chapter_count': len(chapters),
        'content': content,
    })


@csrf_exempt
@require_http_methods(['PUT'])
def book_progress_api(request, book_id: int):
    user, error = require_reader_user(request)
    if error:
        return error
    book = get_object_or_404(Book, id=book_id, user=user)
    payload = json.loads(request.body.decode('utf-8'))
    progress, _ = ReadingProgress.objects.get_or_create(user=user, book=book)
    progress.chapter_index = int(payload.get('chapter_index', progress.chapter_index))
    progress.chapter_href = payload.get('chapter_href', progress.chapter_href)
    progress.locator = payload.get('locator', progress.locator)
    progress.percent = float(payload.get('percent', progress.percent))
    progress.save()
    return JsonResponse({'ok': True})
''',

    'library/epub.py': '''import html
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from django.http import Http404
from bs4 import BeautifulSoup

NS = {
    'opf': 'http://www.idpf.org/2007/opf',
    'dc': 'http://purl.org/dc/elements/1.1/',
    'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
}


def find_opf(zf: ZipFile) -> str:
    container_xml = ET.fromstring(zf.read('META-INF/container.xml'))
    rootfile = container_xml.find('container:rootfiles/container:rootfile', NS)
    if rootfile is None:
        raise Http404('Invalid EPUB: OPF file not found')
    return rootfile.attrib['full-path']


def load_toc_labels(zf: ZipFile, toc_path: str) -> dict[str, str]:
    labels = {}
    if toc_path.endswith('.ncx'):
        root = ET.fromstring(zf.read(toc_path))
        for nav_point in root.findall('.//{*}navPoint'):
            src = nav_point.find('.//{*}content')
            text = nav_point.find('.//{*}text')
            if src is not None and text is not None:
                labels[src.attrib.get('src', '').split('#')[0]] = text.text or 'Chapter'
    else:
        soup = BeautifulSoup(zf.read(toc_path), 'html.parser')
        for link in soup.select('nav a[href]'):
            labels[link['href'].split('#')[0]] = link.get_text(' ', strip=True)
    return labels


def parse_book(epub_path: Path) -> dict:
    with ZipFile(epub_path) as zf:
        opf_path = find_opf(zf)
        opf_dir = Path(opf_path).parent
        opf_root = ET.fromstring(zf.read(opf_path))
        metadata = opf_root.find('opf:metadata', NS)
        manifest = opf_root.find('opf:manifest', NS)
        spine = opf_root.find('opf:spine', NS)
        if manifest is None or spine is None:
            raise Http404('Invalid EPUB: missing manifest or spine')

        title = metadata.findtext('dc:title', default=epub_path.stem, namespaces=NS) if metadata is not None else epub_path.stem
        author = metadata.findtext('dc:creator', default='Unknown author', namespaces=NS) if metadata is not None else 'Unknown author'

        manifest_items = {}
        toc_path = None
        for item in manifest.findall('opf:item', NS):
            manifest_items[item.attrib['id']] = item.attrib
            if item.attrib.get('properties') == 'nav':
                toc_path = str((opf_dir / item.attrib['href']).as_posix())
            if item.attrib.get('id') == spine.attrib.get('toc'):
                toc_path = str((opf_dir / item.attrib['href']).as_posix())

        chapters = []
        for itemref in spine.findall('opf:itemref', NS):
            item = manifest_items.get(itemref.attrib['idref'])
            if not item:
                continue
            href = str((opf_dir / item['href']).as_posix())
            chapters.append({
                'id': itemref.attrib['idref'],
                'href': href,
                'label': Path(item['href']).stem.replace('_', ' ').title(),
            })

        toc_labels = load_toc_labels(zf, toc_path) if toc_path else {}
        for chapter in chapters:
            chapter['label'] = toc_labels.get(chapter['href'], chapter['label'])

        return {'title': title, 'author': author, 'chapters': chapters}


def chapter_html(epub_path: Path, href: str) -> str:
    with ZipFile(epub_path) as zf:
        raw = zf.read(href)
        soup = BeautifulSoup(raw, 'html.parser')
        body = soup.find('body')
        if body is None:
            return '<p>No readable content found.</p>'
        for tag in body.find_all(['script', 'style']):
            tag.decompose()
        for img in body.find_all('img'):
            alt = html.escape(img.get('alt', 'Illustration omitted'))
            img.replace_with(BeautifulSoup(f'<p class="image-note">[{alt}]</p>', 'html.parser'))
        return ''.join(str(node) for node in body.contents)
''',

    'library/migrations/__init__.py': '',

    '.env.example': '''DJANGO_SECRET_KEY=replace-with-a-new-django-secret
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=replace-with-your-public-anon-or-publishable-key
SUPABASE_JWKS_URL=https://your-project.supabase.co/auth/v1/.well-known/jwks.json
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=replace-with-your-db-password
POSTGRES_HOST=aws-1-ap-southeast-2.pooler.supabase.com
POSTGRES_PORT=6543
POSTGRES_SSLMODE=require
''',

    'requirements.txt': '''Django==5.2.1
beautifulsoup4==4.13.4
lxml==5.4.0
PyJWT==2.10.1
requests==2.32.3
python-dotenv==1.0.1
psycopg[binary]==3.2.9
''',

    'README.md': '''# Django EPUB Reader with Supabase Auth

Run the setup script, copy `.env.example` to `.env`, install dependencies, then run Django migrations and the dev server.
''',
}


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip('\n'), encoding='utf-8')


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for relative_path, content in FILES.items():
        write_file(ROOT / relative_path, content)
    print(f'Created project at: {ROOT.resolve()}')
    print('Next steps:')
    print('1. cd django-supabase-epub-reader')
    print('2. cp .env.example .env')
    print('3. Fill in your Supabase and Postgres values')
    print('4. python -m venv .venv && source .venv/bin/activate')
    print('5. pip install -r requirements.txt')
    print('6. python manage.py makemigrations && python manage.py migrate')
    print('7. python manage.py runserver')


if __name__ == '__main__':
    main()