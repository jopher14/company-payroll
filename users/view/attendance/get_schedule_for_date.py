from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from datetime import datetime
from ...models import Schedule
from ..utils import castUser


@login_required
def get_schedule_for_date(request: HttpRequest) -> HttpResponse:
    date_str = request.GET.get("date")
    if not date_str:
        return JsonResponse({"error": "No date provided"}, status=400)

    user = castUser(request)
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    day_number = date_obj.isoweekday()  # Monday=1, Sunday=7

    schedule = Schedule.objects.filter(employee=user, days_of_week__in=[day_number]).first()
    if schedule:
        return JsonResponse({
            "time_in": schedule.time_in.strftime("%H:%M"),
            "time_out": schedule.time_out.strftime("%H:%M"),
        })
    return JsonResponse({"time_in": None, "time_out": None})
