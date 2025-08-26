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
    path(route='attendance/set_schedule/', view=views.set_schedule, name='set_schedule'),

    # Attendance
    path(route="attendance/log/", view=views.log_attendance, name="log_attendance"),
    path(route='attendance/', view=views.attendance_list, name='attendance_list'),
]
