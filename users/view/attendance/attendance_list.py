from typing import cast, Any
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.core.paginator import Paginator
from ...models import User, Attendance


@login_required
def attendance_list(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        return HttpResponse("Invalid user", status=400)

    if user.role == "manager":
        attendances = Attendance.objects.select_related("employee").filter(
            employee__role__in=["supervisor", "employee"]
        ).order_by("-date")
    else:
        attendances = Attendance.objects.filter(
            employee=user,
            employee__role__in=["supervisor", "employee"]
        ).select_related("employee").order_by("-date")

    # Pagination (5 per page)
    paginator = Paginator(attendances, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # ✅ Add late/undertime flags for template
    for att in page_obj:
        att = cast(Any, att)
        schedule = att.employee.schedule.first() if hasattr(att.employee, "schedule") else None
        att.is_late = False
        att.is_undertime = False

        if schedule:
            if att.time_in and att.time_in > schedule.time_in:
                att.is_late = True
            if att.time_out and att.time_out < schedule.time_out:
                att.is_undertime = True

    return render(request, "attendance/attendance_list.html", {
        "page_obj": page_obj,
    })
