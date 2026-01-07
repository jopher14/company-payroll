from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render
from . import views

app_name = "users"


def multi_login_detected_view(request: HttpRequest) -> HttpResponse:
    return render(request, "users/multi_login_detected.html")


urlpatterns = [
    path(route="profile/", view=views.profile_view, name="profile"),

    path(route="login/", view=LoginView.as_view(template_name='users/login.html'), name='login'),
    path(route="logout/", view=LogoutView.as_view(template_name="users/logged_out.html"), name='logout'),

    path(route="multi-login-detected/", view=multi_login_detected_view, name="multi_login_detected"),

    # Change password
    path(route='password_reset/', view=PasswordResetView.as_view(template_name='users/password_reset.html'), name='password_reset'),
    path(route='password_reset/done/', view=PasswordResetDoneView.as_view(template_name='users/password_reset_done.html'), name='password_reset_done'),
    path(route='reset/<uidb64>/<token>/', view=PasswordResetConfirmView.as_view(template_name='users/password_reset_confirm.html'), name='password_reset_confirm'),
    path(route='reset/done/', view=PasswordResetCompleteView.as_view(template_name='users/password_reset_complete.html'), name='password_reset_complete'),

    # HR only
    path(route="register/", view=views.register, name="register"),
    path(route="employees/", view=views.employee_list, name="employee_list"),
    path(route='employees/update/<int:pk>/', view=views.update_employee, name='update_employee'),
    path(route="employees/<int:pk>/delete/", view=views.delete_employee, name="delete_employee"),
    path(route="manage/", view=views.manage_schedule, name="manage_schedule"),
    path(route="add-schedule/", view=views.add_schedule, name="add_schedule"),
    path(route="edit-schedule/<int:pk>/", view=views.edit_schedule, name="edit_schedule"),

    # Manually add edit delete log attendance HR
    path(route="manage-attendance/", view=views.manage_attendance, name="manage_attendance"),
    path(route="edit/<int:attendance_id>/", view=views.manage_attendance, name="edit_attendance"),
    path(route="delete/<int:attendance_id>/", view=views.delete_attendance, name="delete_attendance"),

    # Manually add time in and time out
    path(route="manual-request/", view=views.manual_attendance_request, name="manual_request"),
    path(route="approve/<int:request_id>/", view=views.approve_attendance, name="approve_request"),
    path(route="requests-list/", view=views.attendance_requests, name="attendance_requests"),
    path(route="request/<int:request_id>/edit/", view=views.edit_attendance_request, name="edit_request"),
    path(route="delete-request/<int:request_id>/delete/", view=views.delete_attendance_request, name="delete_request"),


    # Employee
    path(route="leave/file/", view=views.file_leave, name="file_leave"),
    path(route="leave/my_leaves/", view=views.my_leaves, name="my_leaves"),
    path(route="leave/edit/<int:pk>/", view=views.edit_leave, name="edit_leave"),
    path(route="leave/delete/<int:pk>/", view=views.delete_leave, name="delete_leaves"),

    # Supervisor
    path(route="leave/pending/", view=views.pending_leaves, name="pending_leaves"),
    path(route="leave/approve/<int:pk>/", view=views.approve_leave, name="approve_leave"),
    path(route="leave/reject/<int:pk>/", view=views.reject_leave, name="reject_leave"),

    # Manager

    # Attendance
    path(route="attendance/log/", view=views.log_attendance, name="log_attendance"),
    path(route="attendance/upload/", view=views.upload_attendance_csv, name="upload_attendance_csv"),
    path(route='attendance/', view=views.attendance_list, name='attendance_list'),
    path(route="request-schedule-change/", view=views.request_schedule_change, name="request_schedule_change"),
    path(route="pending-schedule-changes/", view=views.pending_schedule_changes, name="pending_schedule_changes"),
    path(route='my-pending-schedule-changes/', view=views.my_pending_schedule_change, name='my_pending_schedule_change'),
    path(route="edit-schedule-change/<int:pk>/", view=views.edit_schedule_change, name="edit_schedule_change"),
    path(route="delete-schedule-change/<int:pk>/", view=views.delete_schedule_change, name="delete_schedule_change"),
    path(route='approve-schedule-change/<int:pk>/', view=views.approve_schedule_change, name='approve_schedule_change'),
    path(route='reject-schedule-change/<int:pk>/', view=views.reject_schedule_change, name='reject_schedule_change'),
    path(route='ajax/get-schedule/', view=views.get_schedule_for_date, name='ajax_get_schedule'),

    # Overtime
    path(route="overtimes/", view=views.overtime_list, name="overtime_list"),
    path(route="overtimes/request/", view=views.overtime_request, name="overtime_request"),
    path(route="overtime/<int:pk>/approve/", view=views.overtime_approve, name="overtime_approve"),
    path(route="overtime/<int:pk>/reject/", view=views.overtime_reject, name="overtime_reject"),
    path(route="overtimes/<int:pk>/edit/", view=views.overtime_edit, name="overtime_edit"),
    path(route="overtimes/<int:pk>/delete/", view=views.overtime_delete, name="overtime_delete"),
    path(route="overtimes/<int:pk>/<str:action>/", view=views.overtime_action, name="overtime_action"),
    path(route="overtime/pending/", view=views.pending_overtimes, name="pending_overtimes"),
    path(route="overtime/my_pending/", view=views.my_pending_overtime, name="my_pending_overtime"),

    # Loans
    path(route="loans/", view=views.manage_loans, name="manage_loans"),
    path(route="create/", view=views.create_loan, name="create_loan"),
    path(route="<int:pk>/edit/", view=views.edit_loan, name="edit_loan"),
    path(route="<int:pk>/delete/", view=views.delete_loan, name="delete_loan"),

    # Team
    path(route="team/", view=views.team_list, name="team_list"),
    path(route="team/create/", view=views.create_team, name="create_team"),
    path(route="team/<int:pk>/edit/", view=views.edit_team, name="edit_team"),
    path(route="team/<int:pk>/delete/", view=views.delete_team, name="delete_team"),
    path(route="my-current-team/", view=views.my_current_team, name="my_current_team"),
]
