from django.db import models


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
