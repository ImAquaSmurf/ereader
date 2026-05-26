import json
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
