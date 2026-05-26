from django.contrib import admin
from .models import ReaderUser, Book, ReadingProgress

admin.site.register(ReaderUser)
admin.site.register(Book)
admin.site.register(ReadingProgress)
