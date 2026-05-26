import json
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
