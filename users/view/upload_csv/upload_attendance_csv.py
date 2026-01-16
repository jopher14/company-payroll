from typing import cast, IO
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.contrib import messages
from django.shortcuts import redirect, render
from datetime import datetime
from ...models import Attendance
from ...forms import AttendanceCSVUploadForm
import csv
import io


@login_required
def upload_attendance_csv(request: HttpRequest) -> HttpResponse:
    """
    Upload a CSV with columns: date,time_in,time_out
    Saves records to Attendance for the logged-in employee.
    Header format must be: date,time_in,time_out
    """
    if request.method == "POST":
        form = AttendanceCSVUploadForm(request.POST, request.FILES)

        # ✅ Check if a file was actually selected
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            messages.error(request, "⚠️ Please select a CSV file before uploading.")
            return render(request, "attendance/upload_csv.html", {"form": form})

        if form.is_valid():
            try:
                # ✅ Tell mypy this is a binary IO stream
                binary_stream = cast(IO[bytes], uploaded_file.file)
                file = io.TextIOWrapper(binary_stream, encoding="utf-8")

                reader = csv.DictReader(file)

                # ✅ Validate headers
                expected_headers = {"date", "time_in", "time_out"}
                if not reader.fieldnames or set(reader.fieldnames) != expected_headers:
                    messages.error(
                        request,
                        f"❌ Invalid CSV headers. Expected: {', '.join(expected_headers)}.",
                    )
                    return render(request, "attendance/upload_csv.html", {"form": form})

                added_count = 0

                for row in reader:
                    try:
                        date = datetime.strptime(row["date"], "%d/%m/%Y").date()
                        time_in = datetime.strptime(row["time_in"], "%H:%M:%S").time()
                        time_out = datetime.strptime(row["time_out"], "%H:%M:%S").time()

                        attendance, created = Attendance.objects.update_or_create(
                            employee=request.user,
                            date=date,
                            defaults={"time_in": time_in, "time_out": time_out},
                        )
                        if created:
                            added_count += 1
                    except ValueError:
                        messages.error(
                            request,
                            "❌ Invalid date or time format in CSV. Use DD/MM/YYYY and HH:MM:SS.",
                        )
                        return render(request, "attendance/upload_csv.html", {"form": form})

                messages.success(
                    request,
                    f"✅ {added_count} attendance records uploaded successfully.",
                )
                return redirect("main:dashboard")

            except Exception:
                messages.error(
                    request, "❌ Unable to read the uploaded file. Make sure it's a valid CSV."
                )
                return render(request, "attendance/upload_csv.html", {"form": form})

    else:
        form = AttendanceCSVUploadForm()

    return render(request, "attendance/upload_csv.html", {"form": form})
