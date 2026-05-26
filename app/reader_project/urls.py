from django.conf import settings
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
