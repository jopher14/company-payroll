from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ...models import Overtime


@login_required
def overtime_delete(request: HttpRequest, pk: int) -> HttpResponse:
    overtime = get_object_or_404(Overtime, pk=pk)

    if request.method == "POST":
        overtime.delete()
        messages.success(request, "🗑️ Overtime request deleted successfully!")
        return redirect("users:my_pending_overtime")

    return render(request, "overtime/overtime_confirm_delete.html", {"overtime": overtime})
