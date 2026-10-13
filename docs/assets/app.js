// Homeward concept prototype. Small progressive enhancements only:
// the site works fully without JavaScript. Nothing here sends, saves or files anything.
(function () {
  function store(key, value) {
    try { if (value === undefined) { return JSON.parse(localStorage.getItem(key) || "null"); } localStorage.setItem(key, JSON.stringify(value)); } catch (err) { return null; }
    return value;
  }
  // Edit a draft in place (kept in this page only; nothing is saved or sent).
  document.querySelectorAll("[data-edit]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var target = document.getElementById(btn.getAttribute("data-edit"));
      if (!target) return;
      var editing = target.getAttribute("contenteditable") === "true";
      target.setAttribute("contenteditable", editing ? "false" : "true");
      btn.textContent = editing ? "Edit draft" : "Done editing";
      if (!editing) target.focus();
    });
  });
  // Show a short explanation for actions that are not simulated in this demo.
  document.querySelectorAll("[data-explain]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var note = document.getElementById(btn.getAttribute("data-explain"));
      if (!note) return;
      note.textContent = btn.getAttribute("data-text");
      note.classList.add("show");
    });
  });
  // Settings toggles (visual only in this demo).
  document.querySelectorAll(".toggle").forEach(function (t) {
    t.addEventListener("click", function () {
      var on = t.getAttribute("aria-pressed") === "true";
      t.setAttribute("aria-pressed", on ? "false" : "true");
      t.textContent = on ? (t.getAttribute("data-off") || "Off") : (t.getAttribute("data-on") || "On");
      var note = document.getElementById("settings-note");
      if (note) note.classList.add("show");
    });
  });
  // Today: items approved or answered in this demo move to "Done this morning" and the counts fall.
  var doneList = document.querySelector('ul.list[data-bucket="done"]');
  if (doneList) {
    var done = store("homeward-done") || [];
    var moved = 0;
    done.forEach(function (slug) {
      var row = document.querySelector('.row[data-slug="' + slug + '"]');
      if (!row || row.parentNode === doneList) return;
      var bucket = row.parentNode.getAttribute("data-bucket");
      document.querySelectorAll('[data-count="' + bucket + '"]').forEach(function (counter) {
        counter.textContent = String(Math.max(0, parseInt(counter.textContent, 10) - 1));
      });
      row.classList.add("done-row");
      var btn = row.querySelector(".btn");
      if (btn) { btn.textContent = "Done"; btn.classList.remove("primary"); }
      doneList.appendChild(row);
      moved += 1;
    });
    var empty = document.querySelector("[data-done-empty]");
    if (empty && moved) empty.textContent = moved + (moved === 1 ? " item done this morning. " : " items done this morning. ") + "Nothing was sent; this is a demo.";
  }
  document.querySelectorAll("[data-reset]").forEach(function (a) {
    a.addEventListener("click", function (ev) {
      ev.preventDefault();
      try { localStorage.removeItem("homeward-done"); } catch (err) {}
      location.href = "index.html";
    });
  });
  // Done pages: say how many are left.
  var rem = document.querySelector("[data-remaining]");
  if (rem) {
    var d = store("homeward-done") || [];
    var total = 11;
    var left = Math.max(0, total - d.length);
    rem.textContent = left === 0 ? "Every item in this demo is done." : left + (left === 1 ? " item" : " items") + " still waiting on Today.";
  }
})();
