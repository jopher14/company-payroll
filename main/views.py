from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpRequest, HttpResponse
from .forms import AnnouncementForm
from .models import Announcement


@login_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "main/dashboard.html")

def is_hr(user):
    return user.role == "human_resources" or user.is_superuser

@login_required
@user_passes_test(is_hr)
def create_announcement(request):
    if request.method == "POST":
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save(commit=False)
            announcement.created_by = request.user
            announcement.save()
            return redirect("main:announcement_list")  # redirect to dashboard or announcements list
    else:
        form = AnnouncementForm()
    return render(request, "announcement/create_announcement.html", {"form": form})

@login_required
def announcement_list(request):
    announcements = Announcement.objects.filter(is_active=True).order_by("-created_at")
    return render(request, "announcement/announcement_list.html", {"announcements": announcements})
