(function () {
  "use strict";

  var shell = document.querySelector(".assistant-shell");
  if (!shell) return;

  var tabs = Array.prototype.slice.call(shell.querySelectorAll("[data-tab-target]"));
  var panels = Array.prototype.slice.call(shell.querySelectorAll("[data-tab-panel]"));

  function activate(name, focusTab) {
    var chosen = tabs.find(function (tab) { return tab.dataset.tabTarget === name; });
    if (!chosen) return;

    tabs.forEach(function (tab) {
      var active = tab === chosen;
      tab.setAttribute("aria-selected", active ? "true" : "false");
      tab.setAttribute("tabindex", active ? "0" : "-1");
    });
    panels.forEach(function (panel) {
      panel.hidden = panel.dataset.tabPanel !== name;
    });
    if (focusTab) chosen.focus();
  }

  tabs.forEach(function (tab, index) {
    tab.addEventListener("click", function () { activate(tab.dataset.tabTarget, false); });
    tab.addEventListener("keydown", function (event) {
      if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return;
      event.preventDefault();
      var direction = event.key === "ArrowRight" ? 1 : -1;
      var next = (index + direction + tabs.length) % tabs.length;
      activate(tabs[next].dataset.tabTarget, true);
    });
  });

  shell.querySelectorAll("[data-go-tab]").forEach(function (button) {
    button.addEventListener("click", function () {
      activate(button.dataset.goTab, true);
      shell.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  var student = shell.querySelector("#analysis-form [name=student_id]");
  var session = shell.querySelector("#analysis-form [name=session_id]");
  function filterSessions() {
    if (!session) return;
    Array.prototype.slice.call(session.options).forEach(function (option) {
      if (!option.value) return;
      option.hidden = Boolean(student && student.value && option.dataset.student !== student.value);
    });
    if (session.selectedOptions[0] && session.selectedOptions[0].hidden) session.value = "";
  }
  if (student) student.addEventListener("change", filterSessions);
  filterSessions();

  activate(shell.dataset.defaultTab || "ask", false);
})();
