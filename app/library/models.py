from django.db import models


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
