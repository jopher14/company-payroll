// Expandable sections
document.querySelectorAll(".expand-toggle").forEach((btn) => {
  btn.addEventListener("click", () => {
    btn.closest(".expandable").classList.toggle("active");
  });
});

// Calendar
document.addEventListener("DOMContentLoaded", function () {
  const calendarEl = document.getElementById("attendance-calendar");

  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: "dayGridMonth",
    height: "auto",
    events: attendanceData,
    eventDisplay: "block",

    eventDidMount: function (info) {
      if (info.event.extendedProps.tooltip) {
        new bootstrap.Tooltip(info.el, {
          title: info.event.extendedProps.tooltip,
          placement: "top",
          trigger: "hover",
          container: "body",
        });
      }
    },
  });

  calendar.render();
});
