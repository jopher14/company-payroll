from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from ...models import Overtime
from ...forms import OvertimeForm


@login_required
def overtime_edit(request: HttpRequest, pk: int) -> HttpResponse:
    overtime = get_object_or_404(Overtime, pk=pk)

    if request.method == "POST":
        form = OvertimeForm(request.POST, instance=overtime)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Overtime request updated successfully!")
            return redirect("users:my_pending_overtime")
    else:
        form = OvertimeForm(instance=overtime)

    return render(request, "overtime/overtime_edit.html", {"form": form})
