from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from .view.profile import profile_view, register, update_employee, delete_employee, employee_list
from .view.leave import file_leave, my_leaves, edit_leave, delete_leave, pending_leaves
from .view.leave.process_leave import approve_leave, reject_leave
from .view.attendance import log_attendance, manage_schedule, add_schedule, edit_schedule, attendance_list, get_schedule_for_date, manage_attendance, delete_attendance
from .view.change_schedule import request_schedule_change, pending_schedule_change, my_pending_schedule_change, approve_schedule_change, reject_schedule_change, edit_schedule_change, delete_schedule_change
from .view.overtime import overtime_request, overtime_list, my_pending_overtime, overtime_approve, overtime_reject, overtime_action, pending_overtimes, overtime_edit, overtime_delete
from .view.loan import manage_loans, create_loan, edit_loan, delete_loan
from .view.team import team_list, create_team, edit_team, delete_team, my_current_team
from .view.upload_csv import manual_attendance_request, upload_attendance_csv, approve_attendance, attendance_requests, edit_attendance_request, delete_attendance_request


app_name = "users"


def multi_login_detected_view(request: HttpRequest) -> HttpResponse:
    return render(request, "users/multi_login_detected.html")


urlpatterns = [
    path(route="profile/", view=profile_view, name="profile"),

    # Login-Logout
    path(route="login/", view=LoginView.as_view(template_name='users/login.html'), name='login'),
    path(route="logout/", view=LogoutView.as_view(template_name="users/logged_out.html"), name='logout'),

    path(route="multi-login-detected/", view=multi_login_detected_view, name="multi_login_detected"),

    # Change password
    path(route='password_reset/', view=PasswordResetView.as_view(template_name='users/password_reset.html'), name='password_reset'),
    path(route='password_reset/done/', view=PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), name='password_reset_done'),
    path(route='reset/<uidb64>/<token>/', view=PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), name='password_reset_confirm'),
    path(route='reset/done/', view=PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), name='password_reset_complete'),

    # HR only
    path(route="register/", view=register, name="register"),
    path(route="employees/", view=employee_list, name="employee_list"),
    path(route='employees/update/<int:pk>/', view=update_employee, name='update_employee'),
    path(route="employees/<int:pk>/delete/", view=delete_employee, name="delete_employee"),
    path(route="manage/", view=manage_schedule, name="manage_schedule"),
    path(route="add-schedule/", view=add_schedule, name="add_schedule"),
    path(route="edit-schedule/<int:pk>/", view=edit_schedule, name="edit_schedule"),

    # Manually add edit delete log attendance HR
    path(route="manage-attendance/", view=manage_attendance, name="manage_attendance"),
    # path(route="edit/<int:attendance_id>/", view=views.manage_attendance, name="edit_attendance"),
    path(route="delete/<int:attendance_id>/", view=delete_attendance, name="delete_attendance"),

    # Manually add time in and time out
    path(route="manual-request/", view=manual_attendance_request, name="manual_request"),
    path(route="approve/<int:request_id>/", view=approve_attendance, name="approve_request"),
    path(route="requests-list/", view=attendance_requests, name="attendance_requests"),
    path(route="request/<int:request_id>/edit/", view=edit_attendance_request, name="edit_request"),
    path(route="delete-request/<int:request_id>/delete/", view=delete_attendance_request, name="delete_request"),


    # Employee
    path(route="leave/file/", view=file_leave, name="file_leave"),
    path(route="leave/my_leaves/", view=my_leaves, name="my_leaves"),
    path(route="leave/edit/<int:pk>/", view=edit_leave, name="edit_leave"),
    path(route="leave/delete/<int:pk>/", view=delete_leave, name="delete_leaves"),

    # Supervisor
    path(route="leave/pending/", view=pending_leaves, name="pending_leaves"),
    path(route="leave/approve/<int:pk>/", view=approve_leave, name="approve_leave"),
    path(route="leave/reject/<int:pk>/", view=reject_leave, name="reject_leave"),

    # Manager

    # Attendance
    path(route="attendance/log/", view=log_attendance, name="log_attendance"),
    path(route="attendance/upload/", view=upload_attendance_csv, name="upload_attendance_csv"),
    path(route='attendance/', view=attendance_list, name='attendance_list'),
    path(route="request-schedule-change/", view=request_schedule_change, name="request_schedule_change"),
    path(route="pending-schedule-changes/", view=pending_schedule_change, name="pending_schedule_changes"),
    path(route='my-pending-schedule-changes/', view=my_pending_schedule_change, name='my_pending_schedule_change'),
    path(route="edit-schedule-change/<int:pk>/", view=edit_schedule_change, name="edit_schedule_change"),
    path(route="delete-schedule-change/<int:pk>/", view=delete_schedule_change, name="delete_schedule_change"),
    path(route='approve-schedule-change/<int:pk>/', view=approve_schedule_change, name='approve_schedule_change'),
    path(route='reject-schedule-change/<int:pk>/', view=reject_schedule_change, name='reject_schedule_change'),
    path(route='ajax/get-schedule/', view=get_schedule_for_date, name='ajax_get_schedule'),

    # Overtime
    path(route="overtimes/", view=overtime_list, name="overtime_list"),
    path(route="overtimes/request/", view=overtime_request, name="overtime_request"),
    path(route="overtime/<int:pk>/approve/", view=overtime_approve, name="overtime_approve"),
    path(route="overtime/<int:pk>/reject/", view=overtime_reject, name="overtime_reject"),
    path(route="overtimes/<int:pk>/edit/", view=overtime_edit, name="overtime_edit"),
    path(route="overtimes/<int:pk>/delete/", view=overtime_delete, name="overtime_delete"),
    path(route="overtimes/<int:pk>/<str:action>/", view=overtime_action, name="overtime_action"),
    path(route="overtime/pending/", view=pending_overtimes, name="pending_overtimes"),
    path(route="overtime/my_pending/", view=my_pending_overtime, name="my_pending_overtime"),

    # Loans
    path(route="loans/", view=manage_loans, name="manage_loans"),
    path(route="create/", view=create_loan, name="create_loan"),
    path(route="<int:pk>/edit/", view=edit_loan, name="edit_loan"),
    path(route="<int:pk>/delete/", view=delete_loan, name="delete_loan"),

    # Team
    path(route="team/", view=team_list, name="team_list"),
    path(route="team/create/", view=create_team, name="create_team"),
    path(route="team/<int:pk>/edit/", view=edit_team, name="edit_team"),
    path(route="team/<int:pk>/delete/", view=delete_team, name="delete_team"),
    path(route="my-current-team/", view=my_current_team, name="my_current_team"),
]
