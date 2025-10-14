from django.contrib import admin
from .models import Announcement
from django.utils.html import format_html


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "event_date",
        "created_by",
        "created_at",
        "is_active",
        "preview_image",
    )
    list_filter = ("is_active", "event_date", "created_at")
    search_fields = ("title", "description")
    readonly_fields = ("created_at", "preview_image")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    @admin.display(description="Image Preview")
    def preview_image(self, obj):
        if obj.picture:
            return format_html(
                '<img src="{}" style="width:60px; height:60px; object-fit:cover; border-radius:8px;" />',
                obj.picture.url,
            )
        return "—"
