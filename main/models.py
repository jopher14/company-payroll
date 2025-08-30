from django.db import models
from django.conf import settings


class Announcement(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    event_date = models.DateField(null=True, blank=True)  # optional field for events
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="announcement_created"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # can deactivate old announcements

    class Meta:
        ordering = ['-created_at']  # latest announcements first

    def __str__(self):
        return f"{self.title} ({'Active' if self.is_active else 'Inactive'})"
