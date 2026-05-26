from django.contrib import admin
from .models import ReaderUser, Book, ReadingProgress, Bookmark, Note

admin.site.register(ReaderUser)
admin.site.register(Book)
admin.site.register(ReadingProgress)
admin.site.register(Bookmark)
admin.site.register(Note)
