from pathlib import Path
import textwrap

ROOT = Path("ebook-reader-app")

FILES = {
    "manage.py": '''#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reader_project.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
''',

    "vercel.json": '''{
  "version": 2,
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python",
      "config": { "runtime": "python3.12" }
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
''',

    "api/index.py": '''import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reader_project.settings")

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
''',

    "reader_project/__init__.py": "",

    "reader_project/settings.py": '''from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-secret-key")
DEBUG = os.getenv("DEBUG", "True") == "True"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost,.vercel.app").split(",") if h.strip()]
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "https://*.vercel.app").split(",") if origin.strip()]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "library",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "library.middleware.SupabaseAuthMiddleware",
]

ROOT_URLCONF = "reader_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "reader_project.wsgi.application"
ASGI_APPLICATION = "reader_project.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "postgres"),
        "USER": os.getenv("POSTGRES_USER", ""),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", ""),
        "PORT": os.getenv("POSTGRES_PORT", "6543"),
        "OPTIONS": {
            "sslmode": os.getenv("POSTGRES_SSLMODE", "require"),
        },
    }
}

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_JWKS_URL = os.getenv(
    "SUPABASE_JWKS_URL",
    f"{os.getenv('SUPABASE_URL', '')}/auth/v1/.well-known/jwks.json" if os.getenv("SUPABASE_URL", "") else ""
)
''',

    "reader_project/urls.py": '''from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from library import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("app/", views.reader_app, name="reader_app"),
    path("api/books/", views.books_api, name="books_api"),
    path("api/books/<int:book_id>/", views.book_detail_api, name="book_detail_api"),
    path("api/books/<int:book_id>/progress/", views.book_progress_api, name="book_progress_api"),
    path("api/books/<int:book_id>/bookmarks/", views.bookmarks_api, name="bookmarks_api"),
    path("api/books/<int:book_id>/notes/", views.notes_api, name="notes_api"),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
''',

    "reader_project/asgi.py": '''import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reader_project.settings")
application = get_asgi_application()
''',

    "reader_project/wsgi.py": '''import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "reader_project.settings")
application = get_wsgi_application()
''',

    "library/__init__.py": "",

    "library/apps.py": '''from django.apps import AppConfig


class LibraryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "library"
''',

    "library/models.py": '''from django.db import models


class ReaderUser(models.Model):
    supabase_user_id = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email or self.supabase_user_id


class Book(models.Model):
    user = models.ForeignKey(ReaderUser, on_delete=models.CASCADE, related_name="books")
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(max_length=255)
    cover_url = models.URLField(blank=True)
    epub_file = models.FileField(upload_to="uploads/epubs/", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_opened_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title


class ReadingProgress(models.Model):
    user = models.ForeignKey(ReaderUser, on_delete=models.CASCADE, related_name="progress_items")
    book = models.OneToOneField(Book, on_delete=models.CASCADE, related_name="progress")
    cfi = models.CharField(max_length=1000, blank=True)
    chapter_label = models.CharField(max_length=255, blank=True)
    percent = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} · {self.book}"


class Bookmark(models.Model):
    user = models.ForeignKey(ReaderUser, on_delete=models.CASCADE, related_name="bookmarks")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="bookmarks")
    cfi = models.CharField(max_length=1000)
    label = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Note(models.Model):
    user = models.ForeignKey(ReaderUser, on_delete=models.CASCADE, related_name="notes")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="notes")
    cfi = models.CharField(max_length=1000)
    quote = models.TextField(blank=True)
    body = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
''',

    "library/admin.py": '''from django.contrib import admin
from .models import ReaderUser, Book, ReadingProgress, Bookmark, Note

admin.site.register(ReaderUser)
admin.site.register(Book)
admin.site.register(ReadingProgress)
admin.site.register(Bookmark)
admin.site.register(Note)
''',

    "library/auth.py": '''import requests
import jwt
from django.conf import settings
from django.http import JsonResponse
from .models import ReaderUser

JWKS_CACHE = None


def get_jwks():
    global JWKS_CACHE
    if JWKS_CACHE is None:
        if not settings.SUPABASE_JWKS_URL:
            raise RuntimeError("SUPABASE_JWKS_URL is not configured")
        JWKS_CACHE = requests.get(settings.SUPABASE_JWKS_URL, timeout=10).json()
    return JWKS_CACHE


def verify_supabase_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    jwks = get_jwks()
    jwk = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
    if not jwk:
        raise ValueError("No matching signing key found")
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
    return jwt.decode(token, public_key, algorithms=["RS256"], options={"verify_aud": False})


def auth_error(message: str, status: int = 401):
    return JsonResponse({"detail": message}, status=status)


def get_user_from_request(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    claims = verify_supabase_token(token)
    user_id = claims.get("sub")
    if not user_id:
        raise ValueError("Missing user id in token")
    user, _ = ReaderUser.objects.get_or_create(
        supabase_user_id=user_id,
        defaults={"email": claims.get("email", "") or ""},
    )
    email = claims.get("email", "") or ""
    if email and user.email != email:
        user.email = email
        user.save(update_fields=["email"])
    return user
''',

    "library/middleware.py": '''from .auth import get_user_from_request


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

    "library/views.py": '''import json
from pathlib import Path
from django.conf import settings
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone

from .auth import auth_error
from .models import Book, ReadingProgress, Bookmark, Note


def home(request):
    return render(request, "index.html", {
        "SUPABASE_URL": settings.SUPABASE_URL,
        "SUPABASE_ANON_KEY": settings.SUPABASE_ANON_KEY,
    })


def reader_app(request):
    return render(request, "app.html", {
        "SUPABASE_URL": settings.SUPABASE_URL,
        "SUPABASE_ANON_KEY": settings.SUPABASE_ANON_KEY,
    })


def require_reader_user(request):
    user = getattr(request, "reader_user", None)
    if not user:
        return None, auth_error("Authentication required")
    return user, None


@csrf_exempt
@require_http_methods(["GET", "POST"])
def books_api(request):
    user, error = require_reader_user(request)
    if error:
        return error

    if request.method == "GET":
        books = Book.objects.filter(user=user).order_by("-last_opened_at", "title")
        return JsonResponse([
            {
                "id": book.id,
                "title": book.title,
                "author": book.author,
                "cover_url": book.cover_url,
                "epub_file_url": book.epub_file.url if book.epub_file else "",
                "progress": book.progress.percent if hasattr(book, "progress") else 0,
                "last_opened_at": book.last_opened_at.isoformat() if book.last_opened_at else None,
            }
            for book in books
        ], safe=False)

    title = (request.POST.get("title") or "Untitled book").strip() or "Untitled book"
    author = (request.POST.get("author") or "Unknown author").strip() or "Unknown author"
    cover_url = (request.POST.get("cover_url") or "").strip()
    epub_file = request.FILES.get("epub_file")

    if not epub_file:
        return JsonResponse({"detail": "EPUB file is required."}, status=400)

    suffix = Path(epub_file.name).suffix.lower()
    if suffix != ".epub":
        return JsonResponse({"detail": "Only .epub files are allowed."}, status=400)

    book = Book.objects.create(
        user=user,
        title=title,
        author=author,
        cover_url=cover_url,
        slug=slugify(title) or f"book-{user.id}",
        last_opened_at=timezone.now(),
    )
    book.epub_file.save(epub_file.name, epub_file, save=True)

    ReadingProgress.objects.get_or_create(
        user=user,
        book=book,
        defaults={"cfi": "", "chapter_label": "", "percent": 0},
    )

    return JsonResponse({
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "cover_url": book.cover_url,
        "epub_file_url": book.epub_file.url if book.epub_file else "",
    })


@require_http_methods(["GET"])
def book_detail_api(request, book_id: int):
    user, error = require_reader_user(request)
    if error:
        return error

    book = get_object_or_404(Book, id=book_id, user=user)
    progress, _ = ReadingProgress.objects.get_or_create(user=user, book=book)

    book.last_opened_at = timezone.now()
    book.save(update_fields=["last_opened_at"])

    return JsonResponse({
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "cover_url": book.cover_url,
        "epub_file_url": book.epub_file.url if book.epub_file else "",
        "progress": {
            "cfi": progress.cfi,
            "chapter_label": progress.chapter_label,
            "percent": progress.percent,
        },
    })


@csrf_exempt
@require_http_methods(["PUT"])
def book_progress_api(request, book_id: int):
    user, error = require_reader_user(request)
    if error:
        return error

    book = get_object_or_404(Book, id=book_id, user=user)
    payload = json.loads(request.body.decode("utf-8")) if request.body else {}

    progress, _ = ReadingProgress.objects.get_or_create(user=user, book=book)
    progress.cfi = payload.get("cfi", progress.cfi)
    progress.chapter_label = payload.get("chapter_label", progress.chapter_label)
    progress.percent = float(payload.get("percent", progress.percent or 0))
    progress.save()

    book.last_opened_at = timezone.now()
    book.save(update_fields=["last_opened_at"])

    return JsonResponse({"ok": True})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def bookmarks_api(request, book_id: int):
    user, error = require_reader_user(request)
    if error:
        return error

    book = get_object_or_404(Book, id=book_id, user=user)

    if request.method == "GET":
        items = Bookmark.objects.filter(user=user, book=book)
        return JsonResponse([
            {
                "id": item.id,
                "cfi": item.cfi,
                "label": item.label,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ], safe=False)

    payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    item = Bookmark.objects.create(
        user=user,
        book=book,
        cfi=payload.get("cfi", ""),
        label=payload.get("label", ""),
    )
    return JsonResponse({
        "id": item.id,
        "cfi": item.cfi,
        "label": item.label,
    })


@csrf_exempt
@require_http_methods(["GET", "POST"])
def notes_api(request, book_id: int):
    user, error = require_reader_user(request)
    if error:
        return error

    book = get_object_or_404(Book, id=book_id, user=user)

    if request.method == "GET":
        items = Note.objects.filter(user=user, book=book)
        return JsonResponse([
            {
                "id": item.id,
                "cfi": item.cfi,
                "quote": item.quote,
                "body": item.body,
                "created_at": item.created_at.isoformat(),
            }
            for item in items
        ], safe=False)

    payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    item = Note.objects.create(
        user=user,
        book=book,
        cfi=payload.get("cfi", ""),
        quote=payload.get("quote", ""),
        body=payload.get("body", ""),
    )
    return JsonResponse({
        "id": item.id,
        "cfi": item.cfi,
        "quote": item.quote,
        "body": item.body,
    })
''',

    "library/migrations/__init__.py": "",

    "templates/index.html": '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Django EPUB Reader</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <div class="landing-shell">
    <header class="landing-header">
      <div>
        <p class="eyebrow">Django · Supabase · EPUB.js</p>
        <h1>EPUB Reader</h1>
        <p class="lead">Upload your EPUB files, keep a reading library, and read them in a cleaner browser-based app.</p>
      </div>
      <a class="btn primary" href="/app/">Open app</a>
    </header>

    <section class="landing-grid">
      <article class="feature-card">
        <h2>Upload EPUB</h2>
        <p>Add your own `.epub` files from your computer instead of only linking to a hosted file. [web:88][web:330]</p>
      </article>
      <article class="feature-card">
        <h2>Browser reader</h2>
        <p>Read uploaded files in the browser with `epub.js`, which is designed for browser EPUB rendering. [web:317][web:315]</p>
      </article>
      <article class="feature-card">
        <h2>Reading tools</h2>
        <p>Bookmarks, notes, progress, themes, and font controls are scaffolded for a more app-like experience. [web:304][web:308]</p>
      </article>
    </section>
  </div>
</body>
</html>
''',

    "templates/app.html": '''<!doctype html>
<html lang="en" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Reader App</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <div class="app-layout">
    <aside class="left-panel">
      <div class="brand-block">
        <p class="eyebrow">Library</p>
        <h1>My Books</h1>
        <p class="muted" id="auth-status">Checking session...</p>
      </div>

      <section class="panel-card" id="login-panel">
        <h2>Email sign in</h2>
        <p class="muted">Use your email to receive a magic link.</p>
        <form id="login-form" class="stack-form">
          <label for="email-input">Email</label>
          <input id="email-input" name="email" type="email" autocomplete="email" placeholder="you@example.com" required>
          <button class="btn primary full-width" type="submit">Send magic link</button>
        </form>
        <p class="inline-message" id="login-message"></p>
      </section>

      <section class="panel-card" id="user-panel" hidden>
        <div class="toolbar-row">
          <button class="btn ghost" id="sign-out-btn" type="button">Sign out</button>
          <button class="btn primary" id="load-books-btn" type="button">Refresh</button>
        </div>

        <form id="upload-form" class="stack-form compact-form" enctype="multipart/form-data">
          <label for="book-title">Title</label>
          <input id="book-title-input" name="title" type="text" placeholder="Book title" required>

          <label for="book-author">Author</label>
          <input id="book-author-input" name="author" type="text" placeholder="Author">

          <label for="book-cover-url">Cover URL</label>
          <input id="book-cover-url-input" name="cover_url" type="url" placeholder="https://example.com/cover.jpg">

          <label for="epub-file-input">EPUB file</label>
          <input id="epub-file-input" name="epub_file" type="file" accept=".epub,application/epub+zip" required>

          <button class="btn primary full-width" type="submit">Upload EPUB</button>
        </form>
        <p class="inline-message" id="upload-message"></p>
      </section>

      <section class="panel-card">
        <div class="section-head">
          <h2>Continue reading</h2>
        </div>
        <div id="continue-reading" class="empty-state small-empty">
          <p>No recent book yet.</p>
        </div>
      </section>

      <section class="panel-card grow-panel">
        <div class="section-head">
          <h2>Library</h2>
        </div>
        <div id="book-list" class="book-list">
          <div class="empty-state small-empty"><p>Sign in to see your books.</p></div>
        </div>
      </section>
    </aside>

    <main class="reader-shell">
      <header class="reader-toolbar">
        <div>
          <p class="eyebrow">Reader</p>
          <h2 id="active-book-title">Welcome</h2>
          <p id="active-book-author" class="muted">Upload or open a book to start reading.</p>
        </div>

        <div class="toolbar-actions">
          <button class="btn ghost" id="theme-btn" type="button">Theme</button>
          <button class="btn ghost" id="font-minus-btn" type="button">A-</button>
          <button class="btn ghost" id="font-plus-btn" type="button">A+</button>
          <button class="btn ghost" id="bookmark-btn" type="button">Bookmark</button>
          <button class="btn ghost" id="note-btn" type="button">Note</button>
        </div>
      </header>

      <section class="reader-main-grid">
        <aside class="reader-sidecard">
          <div class="section-head">
            <h3>Contents</h3>
          </div>
          <div id="toc-list" class="toc-list">
            <p class="muted">Open a book to load its table of contents.</p>
          </div>

          <div class="section-head section-gap">
            <h3>Bookmarks</h3>
          </div>
          <div id="bookmark-list" class="mini-list">
            <p class="muted">No bookmarks yet.</p>
          </div>

          <div class="section-head section-gap">
            <h3>Notes</h3>
          </div>
          <div id="note-list" class="mini-list">
            <p class="muted">No notes yet.</p>
          </div>
        </aside>

        <section class="reader-stage">
          <div id="reader-loading" class="reader-state">
            <p>Choose or upload a book to start reading.</p>
          </div>
          <div id="viewer" class="viewer" hidden></div>
        </section>
      </section>
    </main>
  </div>

  <script>
    window.APP_CONFIG = {
      supabaseUrl: "{{ SUPABASE_URL|escapejs }}",
      supabaseAnonKey: "{{ SUPABASE_ANON_KEY|escapejs }}"
    };
  </script>
  <script src="https://cdn.jsdelivr.net/npm/epubjs/dist/epub.min.js"></script>
  <script src="/static/app.js" defer></script>
</body>
</html>
''',

    "static/style.css": ''':root,
[data-theme="light"] {
  --bg: #f5f3ee;
  --surface: #ffffff;
  --surface-2: #faf8f4;
  --text: #211d17;
  --muted: #6e685d;
  --border: #ddd6cb;
  --primary: #0f6d72;
  --primary-strong: #0b5659;
  --danger: #b13f48;
  --reader-bg: #fffdf9;
  --shadow: 0 8px 28px rgba(29, 23, 16, 0.08);
}

[data-theme="dark"] {
  --bg: #161513;
  --surface: #1d1c1a;
  --surface-2: #252421;
  --text: #ece6dd;
  --muted: #aea79a;
  --border: #37342f;
  --primary: #5fa3aa;
  --primary-strong: #82bcc1;
  --danger: #e17d87;
  --reader-bg: #1b1a18;
  --shadow: 0 12px 30px rgba(0, 0, 0, 0.3);
}

* { box-sizing: border-box; }

html, body {
  margin: 0;
  min-height: 100%;
  font-family: Inter, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
}

body { font-size: 16px; }
h1, h2, h3, p { margin-top: 0; }
button, input { font: inherit; }

input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  color: var(--text);
  padding: 12px 14px;
}

.eyebrow {
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--muted);
  font-size: 12px;
}

.muted { color: var(--muted); }

.btn {
  border: 0;
  border-radius: 999px;
  padding: 11px 16px;
  cursor: pointer;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn.primary {
  background: var(--primary);
  color: white;
}

.btn.ghost {
  background: var(--surface-2);
  color: var(--text);
  border: 1px solid var(--border);
}

.full-width { width: 100%; }

.landing-shell {
  max-width: 1100px;
  margin: 0 auto;
  padding: 32px 24px 56px;
}

.landing-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: flex-start;
  margin-bottom: 32px;
}

.landing-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

.feature-card,
.panel-card,
.left-panel,
.reader-toolbar,
.reader-sidecard,
.reader-stage {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  box-shadow: var(--shadow);
}

.feature-card,
.panel-card,
.reader-toolbar,
.reader-sidecard,
.reader-stage {
  padding: 20px;
}

.app-layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 24px;
  min-height: 100vh;
  padding: 20px;
}

.left-panel {
  padding: 20px;
  display: grid;
  gap: 16px;
  align-content: start;
}

.grow-panel { min-height: 280px; }
.brand-block h1 { margin-bottom: 8px; }

.stack-form {
  display: grid;
  gap: 10px;
}

.compact-form label {
  font-size: 14px;
  color: var(--muted);
}

.inline-message {
  min-height: 22px;
  margin: 10px 0 0;
  color: var(--muted);
}

.inline-message.error {
  color: var(--danger);
}

.toolbar-row,
.toolbar-actions,
.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-gap {
  margin-top: 22px;
}

.book-list,
.mini-list,
.toc-list {
  display: grid;
  gap: 10px;
}

.book-card,
.mini-item,
.toc-item {
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface-2);
  padding: 12px 14px;
}

.book-card {
  cursor: pointer;
  text-align: left;
}

.book-card strong,
.book-card span {
  display: block;
}

.reader-shell {
  display: grid;
  gap: 20px;
  align-content: start;
}

.reader-toolbar {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.reader-main-grid {
  display: grid;
  grid-template-columns: 290px minmax(0, 1fr);
  gap: 20px;
}

.reader-sidecard {
  align-self: start;
  position: sticky;
  top: 20px;
  max-height: calc(100vh - 40px);
  overflow: auto;
}

.reader-stage {
  min-height: calc(100vh - 160px);
  background: var(--reader-bg);
  display: flex;
  align-items: stretch;
  justify-content: stretch;
}

.reader-state {
  margin: auto;
  color: var(--muted);
  text-align: center;
}

.viewer {
  width: 100%;
  height: calc(100vh - 200px);
  min-height: 680px;
}

.empty-state.small-empty {
  padding: 12px 0;
  color: var(--muted);
}

.meta-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  color: var(--muted);
  margin-top: 6px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: var(--border);
  overflow: hidden;
  margin-top: 10px;
}

.progress-fill {
  height: 100%;
  background: var(--primary);
}

.note-quote {
  font-size: 13px;
  color: var(--muted);
  margin-bottom: 6px;
}

@media (max-width: 1100px) {
  .app-layout,
  .reader-main-grid,
  .landing-grid,
  .landing-header {
    grid-template-columns: 1fr;
    display: grid;
  }

  .reader-toolbar {
    flex-direction: column;
  }

  .reader-sidecard {
    position: static;
    max-height: none;
  }

  .viewer {
    min-height: 520px;
    height: 70vh;
  }
}
''',

    "static/app.js": '''let supabaseClient = null;
let currentUser = null;
let currentBook = null;
let bookInstance = null;
let rendition = null;
let fontScale = 100;
let darkTheme = false;

async function getSupabase() {
  if (supabaseClient) return supabaseClient;
  const { createClient } = await import("https://cdn.jsdelivr.net/npm/@supabase/supabase-js/+esm");
  const url = window.APP_CONFIG?.supabaseUrl;
  const key = window.APP_CONFIG?.supabaseAnonKey;
  if (!url || !key) throw new Error("Missing Supabase frontend config");
  supabaseClient = createClient(url, key);
  return supabaseClient;
}

async function getAccessToken() {
  const supabase = await getSupabase();
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token || null;
}

async function authFetch(url, options = {}) {
  const token = await getAccessToken();
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(url, { ...options, headers });
}

function setMessage(id, message, isError = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message || "";
  el.classList.toggle("error", isError);
}

function setSignedInUI(user) {
  document.getElementById("login-panel").hidden = !!user;
  document.getElementById("user-panel").hidden = !user;
  document.getElementById("auth-status").textContent = user ? `Signed in as ${user.email}` : "Signed out";
  if (!user) {
    document.getElementById("book-list").innerHTML = '<div class="empty-state small-empty"><p>Sign in to see your books.</p></div>';
    document.getElementById("continue-reading").innerHTML = "<p>No recent book yet.</p>";
  }
}

async function signInWithEmail(email) {
  const supabase = await getSupabase();
  const redirectTo = `${window.location.origin}/app/`;
  const { error } = await supabase.auth.signInWithOtp({
    email,
    options: { emailRedirectTo: redirectTo }
  });
  if (error) throw error;
}

async function signOut() {
  const supabase = await getSupabase();
  await supabase.auth.signOut();
  currentUser = null;
  setSignedInUI(null);
}

async function refreshAuthStatus() {
  const supabase = await getSupabase();
  const { data } = await supabase.auth.getUser();
  currentUser = data.user || null;
  setSignedInUI(currentUser);
}

function escapeHtml(value) {
  return String(value || "").replace(/[&<>"']/g, function(char) {
    return ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;"
    })[char];
  });
}

function renderContinueReading(books) {
  const target = document.getElementById("continue-reading");
  if (!books.length) {
    target.innerHTML = "<p>No recent book yet.</p>";
    return;
  }
  const book = books[0];
  target.innerHTML = `
    <button class="book-card" type="button" data-book-open="${book.id}">
      <strong>${escapeHtml(book.title)}</strong>
      <span>${escapeHtml(book.author || "Unknown author")}</span>
      <div class="progress-bar"><div class="progress-fill" style="width:${Math.round(book.progress || 0)}%"></div></div>
      <div class="meta-row">
        <span>${Math.round(book.progress || 0)}% read</span>
        <span>Continue</span>
      </div>
    </button>
  `;
  target.querySelector("[data-book-open]")?.addEventListener("click", () => openBook(book.id));
}

function renderBooks(books) {
  const container = document.getElementById("book-list");
  if (!books.length) {
    container.innerHTML = '<div class="empty-state small-empty"><p>No books yet. Upload one above.</p></div>';
    renderContinueReading([]);
    return;
  }

  renderContinueReading(books);

  container.innerHTML = books.map(book => `
    <button class="book-card" type="button" data-book-id="${book.id}">
      <strong>${escapeHtml(book.title)}</strong>
      <span>${escapeHtml(book.author || "Unknown author")}</span>
      <div class="progress-bar"><div class="progress-fill" style="width:${Math.round(book.progress || 0)}%"></div></div>
      <div class="meta-row">
        <span>${Math.round(book.progress || 0)}%</span>
        <span>${book.epub_file_url ? "Uploaded" : "Missing file"}</span>
      </div>
    </button>
  `).join("");

  container.querySelectorAll("[data-book-id]").forEach(button => {
    button.addEventListener("click", () => openBook(button.dataset.bookId));
  });
}

async function loadBooks() {
  const res = await authFetch("/api/books/");
  if (!res.ok) {
    setMessage("login-message", "You need to sign in first.", true);
    return;
  }
  const books = await res.json();
  renderBooks(books);
}

async function uploadBook(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const formData = new FormData(form);

  const file = formData.get("epub_file");
  if (!(file instanceof File) || !file.name) {
    setMessage("upload-message", "Please choose an EPUB file.", true);
    return;
  }

  if (!file.name.toLowerCase().endsWith(".epub")) {
    setMessage("upload-message", "Only .epub files are allowed.", true);
    return;
  }

  setMessage("upload-message", "Uploading EPUB...");

  const res = await authFetch("/api/books/", {
    method: "POST",
    body: formData
  });

  if (!res.ok) {
    let detail = "Upload failed.";
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch (error) {}
    setMessage("upload-message", detail, true);
    return;
  }

  setMessage("upload-message", "Upload complete.");
  form.reset();
  await loadBooks();
}

function renderToc(toc) {
  const target = document.getElementById("toc-list");
  if (!toc.length) {
    target.innerHTML = "<p class='muted'>No table of contents found.</p>";
    return;
  }

  target.innerHTML = toc.map((item, index) => `
    <button class="toc-item" type="button" data-toc-index="${index}">
      ${escapeHtml(item.label || item.href || `Section ${index + 1}`)}
    </button>
  `).join("");

  target.querySelectorAll("[data-toc-index]").forEach(btn => {
    btn.addEventListener("click", () => {
      const index = Number(btn.dataset.tocIndex);
      const item = toc[index];
      if (item && rendition) rendition.display(item.href);
    });
  });
}

function renderBookmarks(items) {
  const target = document.getElementById("bookmark-list");
  if (!items.length) {
    target.innerHTML = "<p class='muted'>No bookmarks yet.</p>";
    return;
  }
  target.innerHTML = items.map(item => `
    <div class="mini-item">
      <strong>${escapeHtml(item.label || "Saved bookmark")}</strong>
      <div class="meta-row"><span>${new Date(item.created_at).toLocaleString()}</span></div>
    </div>
  `).join("");
}

function renderNotes(items) {
  const target = document.getElementById("note-list");
  if (!items.length) {
    target.innerHTML = "<p class='muted'>No notes yet.</p>";
    return;
  }
  target.innerHTML = items.map(item => `
    <div class="mini-item">
      <div class="note-quote">${escapeHtml(item.quote || "No quote")}</div>
      <strong>${escapeHtml(item.body || "Untitled note")}</strong>
      <div class="meta-row"><span>${new Date(item.created_at).toLocaleString()}</span></div>
    </div>
  `).join("");
}

async function loadBookmarks(bookId) {
  const res = await authFetch(`/api/books/${bookId}/bookmarks/`);
  if (!res.ok) return;
  renderBookmarks(await res.json());
}

async function loadNotes(bookId) {
  const res = await authFetch(`/api/books/${bookId}/notes/`);
  if (!res.ok) return;
  renderNotes(await res.json());
}

function applyReaderTheme() {
  document.documentElement.setAttribute("data-theme", darkTheme ? "dark" : "light");
  if (rendition && rendition.themes) {
    rendition.themes.default({
      body: {
        "background": darkTheme ? "#1b1a18" : "#fffdf9",
        "color": darkTheme ? "#ece6dd" : "#211d17",
        "font-size": `${fontScale}%`,
        "line-height": "1.7"
      }
    });
  }
}

async function saveProgress(location) {
  if (!currentBook || !location || !location.start) return;
  const cfi = location.start.cfi || "";
  const current = location.start.displayed;
  const percent = current && current.total ? (current.page / current.total) * 100 : 0;
  const chapterLabel = location.start.href || "";

  await authFetch(`/api/books/${currentBook.id}/progress/`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      cfi,
      chapter_label: chapterLabel,
      percent
    })
  });
}

function attachRenditionEvents() {
  rendition.on("relocated", async (location) => {
    await saveProgress(location);
  });

  rendition.on("rendered", () => {
    applyReaderTheme();
  });
}

async function openBook(bookId) {
  const detailRes = await authFetch(`/api/books/${bookId}/`);
  if (!detailRes.ok) {
    setMessage("upload-message", "Could not load book details.", true);
    return;
  }

  const book = await detailRes.json();
  currentBook = book;

  document.getElementById("active-book-title").textContent = book.title;
  document.getElementById("active-book-author").textContent = book.author || "Unknown author";

  await loadBookmarks(bookId);
  await loadNotes(bookId);

  const loading = document.getElementById("reader-loading");
  const viewer = document.getElementById("viewer");

  if (!book.epub_file_url) {
    loading.hidden = false;
    viewer.hidden = true;
    loading.innerHTML = "<p>This book does not have an uploaded EPUB file yet.</p>";
    return;
  }

  loading.hidden = true;
  viewer.hidden = false;
  viewer.innerHTML = "";

  bookInstance = ePub(book.epub_file_url);
  rendition = bookInstance.renderTo("viewer", {
    width: "100%",
    height: "100%"
  });

  attachRenditionEvents();

  try {
    const navigation = await bookInstance.loaded.navigation;
    renderToc(navigation.toc || []);
  } catch (error) {
    renderToc([]);
  }

  try {
    await rendition.display(book.progress?.cfi || undefined);
  } catch (error) {
    await rendition.display();
  }

  applyReaderTheme();
}

async function addBookmark() {
  if (!currentBook || !rendition || !rendition.currentLocation()) return;
  const location = rendition.currentLocation();
  const cfi = location.start?.cfi || "";
  const label = currentBook.title + " bookmark";

  const res = await authFetch(`/api/books/${currentBook.id}/bookmarks/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cfi, label })
  });

  if (res.ok) await loadBookmarks(currentBook.id);
}

async function addNote() {
  if (!currentBook || !rendition || !rendition.currentLocation()) return;
  const body = window.prompt("Write your note");
  if (!body) return;

  const location = rendition.currentLocation();
  const cfi = location.start?.cfi || "";
  const quote = location.start?.href || "";

  const res = await authFetch(`/api/books/${currentBook.id}/notes/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ cfi, quote, body })
  });

  if (res.ok) await loadNotes(currentBook.id);
}

async function handleLoginSubmit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const email = form.email.value.trim();

  if (!email) {
    setMessage("login-message", "Please enter your email.", true);
    return;
  }

  setMessage("login-message", "Sending magic link...");
  try {
    await signInWithEmail(email);
    setMessage("login-message", "Magic link sent. Check your inbox.");
    form.reset();
  } catch (error) {
    setMessage("login-message", error.message || "Sign-in failed.", true);
  }
}

function bindUI() {
  document.getElementById("login-form").addEventListener("submit", handleLoginSubmit);
  document.getElementById("upload-form").addEventListener("submit", uploadBook);
  document.getElementById("sign-out-btn").addEventListener("click", signOut);
  document.getElementById("load-books-btn").addEventListener("click", loadBooks);
  document.getElementById("theme-btn").addEventListener("click", () => {
    darkTheme = !darkTheme;
    applyReaderTheme();
  });
  document.getElementById("font-plus-btn").addEventListener("click", () => {
    fontScale = Math.min(fontScale + 10, 180);
    applyReaderTheme();
  });
  document.getElementById("font-minus-btn").addEventListener("click", () => {
    fontScale = Math.max(fontScale - 10, 70);
    applyReaderTheme();
  });
  document.getElementById("bookmark-btn").addEventListener("click", addBookmark);
  document.getElementById("note-btn").addEventListener("click", addNote);
}

async function init() {
  bindUI();
  await refreshAuthStatus();
  if (currentUser) await loadBooks();

  const supabase = await getSupabase();
  supabase.auth.onAuthStateChange(async () => {
    await refreshAuthStatus();
    if (currentUser) await loadBooks();
  });
}

init();
''',

    ".env.example": '''DJANGO_SECRET_KEY=replace-with-a-random-django-secret
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,.vercel.app
CSRF_TRUSTED_ORIGINS=https://*.vercel.app

POSTGRES_DB=postgres
POSTGRES_HOST=aws-1-ap-southeast-2.pooler.supabase.com
POSTGRES_PORT=6543
POSTGRES_USER=postgres.your_project_ref
POSTGRES_PASSWORD=replace-with-your-db-password
POSTGRES_SSLMODE=require

SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=replace-with-your-public-anon-or-publishable-key
SUPABASE_JWKS_URL=https://your-project-ref.supabase.co/auth/v1/.well-known/jwks.json
''',

    "requirements.txt": '''Django==5.2.1
PyJWT==2.10.1
requests==2.32.3
python-dotenv==1.0.1
psycopg[binary]==3.2.9
''',

    "README.md": '''# Django EPUB Reader with Uploads

## Features

- Email magic-link sign-in with Supabase
- Upload `.epub` files from the browser
- Django file storage via `MEDIA_ROOT`
- Browser EPUB rendering with `epub.js`
- Continue reading section
- Reading progress saving
- Bookmarks
- Notes
- Theme and font controls

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## Supabase Auth redirect URLs

Add these in Supabase Auth:
- `http://127.0.0.1:8000/**`
- `http://localhost:8000/**`
- your production Vercel URL

## Notes

- This version uploads EPUB files into Django media storage for local development.
- Django handles uploaded files through `request.FILES` and media storage. [web:88][web:330]
- `epub.js` can render EPUB content in the browser from a served file URL, and browser-side workflows can also use blob or binary sources. [web:317][web:331][web:336]
- For production on Vercel, local filesystem uploads are not persistent, so switch the `epub_file` storage to Supabase Storage or another object store. Signed upload flows are supported by Supabase Storage. [web:325][web:326][web:327]
''',
}


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content).lstrip("\\n"), encoding="utf-8")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    for relative_path, content in FILES.items():
        write_file(ROOT / relative_path, content)
    print(f"Created project at: {ROOT.resolve()}")
    print("Next steps:")
    print("1. cd ebook-reader-app")
    print("2. copy .env.example to .env and fill in your values")
    print("3. python -m venv .venv")
    print("4. activate the venv")
    print("5. pip install -r requirements.txt")
    print("6. python manage.py makemigrations && python manage.py migrate")
    print("7. python manage.py runserver")


if __name__ == "__main__":
    main()