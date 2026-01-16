from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from datetime import datetime, timedelta
from ...models import User
from ...forms import OvertimeForm


@login_required
def overtime_request(request: HttpRequest) -> HttpResponse:
    user = request.user
    if not isinstance(user, User):
        return HttpResponse("Invalid user", status=400)

    # 🚫 Restrict to Supervisor & Employee only
    if user.role not in ["supervisor", "employee"]:
        messages.error(request, "You are not allowed to file overtime requests.")
        return redirect("users:my_pending_overtime")

    if request.method == "POST":
        form = OvertimeForm(request.POST)
        if form.is_valid():
            overtime = form.save(commit=False)
            overtime.employee = user

            # ✅ Calculate hours safely in backend if time_in/out provided
            date = form.cleaned_data.get("date")
            time_in = form.cleaned_data.get("time_in")
            time_out = form.cleaned_data.get("time_out")

            if date and time_in and time_out:
                start_dt = datetime.combine(date, time_in)
                end_dt = datetime.combine(date, time_out)

                # Handle overnight shifts (e.g. 10PM → 2AM)
                if end_dt < start_dt:
                    end_dt += timedelta(days=1)

                diff = end_dt - start_dt
                overtime.hours = round(diff.total_seconds() / 3600, 2)

            overtime.overtime_type = form.cleaned_data.get("overtime_type", "ordinary")

            overtime.save()
            messages.success(request, "✅ Overtime request submitted successfully!")
            return redirect("users:my_pending_overtime")
    else:
        form = OvertimeForm()

    return render(request, "overtime/overtime_request.html", {"form": form})
