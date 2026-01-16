from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from ..utils import castUser
from ...models import ScheduleChangeRequest


@login_required
def my_pending_schedule_change(request: HttpRequest) -> HttpResponse:
    user = castUser(request)

    # Get only the pending schedule change requests of the logged-in user
    pending_requests = ScheduleChangeRequest.objects.filter(employee=user, status='pending').order_by('-created_at')

    context = {
        'pending_requests': pending_requests,
    }
    return render(request, 'attendance/my_pending_schedule_change.html', context)
