from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from ...models import Leave, User
from django.utils.timezone import now


@login_required
def process_leave(request: HttpRequest, pk: int, action: str) -> HttpResponse:
    """
    Process a leave request (approve or reject).
    """
    leave = get_object_or_404(Leave, pk=pk)
    reviewer = request.user

    if not isinstance(reviewer, User):
        return HttpResponse("Invalid user", status=400)

    # ✅ Approval hierarchy rules
    if leave.employee.role == "employee" and reviewer.role != "supervisor":
        return HttpResponse("Only supervisors can process employee leaves.", status=403)

    if leave.employee.role == "supervisor" and reviewer.role != "manager":
        return HttpResponse("Only managers can process supervisor leaves.", status=403)

    if leave.status != Leave.PENDING:
        messages.warning(request, "This leave request has already been processed.")
    else:
        if action == "approve":
            leave.status = Leave.APPROVED
            action_msg = "approved"
        elif action == "reject":
            leave.status = Leave.REJECTED
            action_msg = "rejected"
        else:
            return HttpResponse("Invalid action", status=400)

        leave.reviewed_by = reviewer
        leave.reviewed_at = now()
        leave.save()

        messages.success(
            request,
            f"Leave for {leave.employee.get_full_name() or leave.employee.username} {action_msg}."
        )

    return redirect("users:pending_leaves")


# ✅ Shortcut wrappers for URLs
@login_required
def approve_leave(request: HttpRequest, pk: int) -> HttpResponse:
    return process_leave(request, pk, "approve")


@login_required
def reject_leave(request: HttpRequest, pk: int) -> HttpResponse:
    return process_leave(request, pk, "reject")
