from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
from . import views

app_name = "users"

urlpatterns = [
    path(route="login/", view=LoginView.as_view(template_name='users/login.html'), name='login'),
    path(route="logout/", view=LogoutView.as_view(template_name="users/logged_out.html"), name='logout'),

    # HR only
    path(route="register/", view=views.register, name="register"),
    path(route="employees/", view=views.employee_list, name="employee_list"),
    path(route='employee/update/<int:pk>/', view=views.update_employee, name='update_employee'),
    path(route="employees/<int:pk>/delete/", view=views.delete_employee, name="delete_employee"),
    path(route="manage/", view=views.manage_schedule, name="manage_schedule"),
    path(route="add-schedule/", view=views.add_schedule, name="add_schedule"),
    path(route="edit-schedule/<int:pk>/", view=views.edit_schedule, name="edit_schedule"),

    # Employee
    path(route="leave/file/", view=views.file_leave, name="file_leave"),
    path(route="leave/my/", view=views.my_leaves, name="my_leaves"),
    path(route="leave/edit/<int:pk>/", view=views.edit_leave, name="edit_leave"),
    path(route="leave/delete/<int:pk>/", view=views.delete_leave, name="delete_leave"),

    # Supervisor
    path(route="leave/pending/", view=views.pending_leaves, name="pending_leaves"),
    path(route="leave/approve/<int:pk>/", view=views.approve_leave, name="approve_leave"),
    path(route="leave/reject/<int:pk>/", view=views.reject_leave, name="reject_leave"),

    # Manager

    # Attendance
    path(route="attendance/log/", view=views.log_attendance, name="log_attendance"),
    path(route='attendance/', view=views.attendance_list, name='attendance_list'),
    path(route="request-schedule-change/", view=views.request_schedule_change, name="request_schedule_change"),
    path(route="pending-schedule-changes/", view=views.pending_schedule_changes, name="pending_schedule_changes"),
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
]
