function getCsrfToken() {
  const input = document.querySelector("#csrf-form input[name='csrfmiddlewaretoken']");
  return input ? input.value : "";
}

async function apiGetJson(url) {
  const res = await fetch(url, { credentials: "same-origin" });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = data && data.error ? data.error : "Request failed";
    throw new Error(message);
  }
  return data;
}

async function apiSendJson(method, url, payload) {
  const csrf = getCsrfToken();
  const res = await fetch(url, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrf,
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const message = data && data.error ? data.error : "Request failed";
    throw new Error(message);
  }
  return data;
}

function el(id) {
  return document.getElementById(id);
}

function formatDueDate(isoDate) {
  // Keep simple: isoDate is YYYY-MM-DD
  return isoDate;
}

function clear(elNode) {
  while (elNode.firstChild) elNode.removeChild(elNode.firstChild);
}

function renderTasks(tasks) {
  const list = el("task-list");
  const empty = el("tasks-empty");
  if (!list || !empty) return;

  clear(list);

  if (!tasks || tasks.length === 0) {
    empty.style.display = "block";
    return;
  }
  empty.style.display = "none";

  for (const task of tasks) {
    const row = document.createElement("li");
    row.className = "task-row";
    if (task.completed) row.classList.add("is-done");

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = !!task.completed;
    checkbox.addEventListener("change", async () => {
      const prevDone = row.classList.contains("is-done");
      try {
        row.classList.toggle("is-done", checkbox.checked);
        await apiSendJson("PATCH", `/api/tasks/${task.id}/`, { completed: checkbox.checked });
      } catch (err) {
        row.classList.toggle("is-done", prevDone);
        console.error(err);
        showUiError(err.message || "Failed to update task");
      }
    });

    const title = document.createElement("div");
    title.className = "task-title";
    title.textContent = task.title;

    const rightMeta = document.createElement("div");
    rightMeta.className = "task-meta";
    rightMeta.textContent = `Due: ${formatDueDate(task.due_date)}`;

    const actions = document.createElement("div");
    actions.className = "task-actions";
    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "Delete";
    del.addEventListener("click", async () => {
      try {
        await apiSendJson("DELETE", `/api/tasks/${task.id}/`);
        const refreshed = await apiGetJson("/api/tasks/");
        renderTasks(refreshed.tasks);
      } catch (err) {
        console.error(err);
        showUiError(err.message || "Failed to delete task");
      }
    });
    actions.appendChild(del);

    row.appendChild(checkbox);
    row.appendChild(title);
    row.appendChild(rightMeta);
    row.appendChild(actions);
    list.appendChild(row);
  }
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (ch) => {
    switch (ch) {
      case "&":
        return "&amp;";
      case "<":
        return "&lt;";
      case ">":
        return "&gt;";
      case '"':
        return "&quot;";
      case "'":
        return "&#039;";
      default:
        return ch;
    }
  });
}

let uiErrorTimeout = null;
function showUiError(message) {
  const section = document.querySelector("section.panel");
  let box = el("ui-error");

  if (!box) {
    box = document.createElement("div");
    box.id = "ui-error";
    box.className = "banner banner-error";
    box.style.display = "none";
    if (section) section.prepend(box);
    else document.body.prepend(box);
  }

  box.textContent = message;
  box.style.display = "block";
  if (uiErrorTimeout) clearTimeout(uiErrorTimeout);
  uiErrorTimeout = setTimeout(() => {
    box.style.display = "none";
  }, 5000);
}

async function bootHome() {
  const profileWarning = el("profile-warning");
  const uniSelect = el("university-select");
  const saveUniBtn = el("university-save");

  const me = await apiGetJson("/api/me/");
  const profile = me.profile || {};

  if (!uniSelect) return;

  // Populate university selector
  clear(uniSelect);
  for (const uni of me.universities) {
    const opt = document.createElement("option");
    opt.value = uni.id;
    opt.textContent = uni.name;
    uniSelect.appendChild(opt);
  }

  const currentUni = profile.university ? profile.university.name : null;
  const currentUniEl = el("current-university");
  if (currentUniEl) currentUniEl.textContent = currentUni ? currentUni : "No university selected";

  if (!profile.university) {
    if (profileWarning) profileWarning.style.display = "block";
    const addForm = el("add-task-form");
    if (addForm) addForm.style.display = "none";
  } else {
    uniSelect.value = profile.university.id;
  }

  if (saveUniBtn) {
    saveUniBtn.addEventListener("click", async () => {
      try {
        const university_id = Number(uniSelect.value);
        await apiSendJson("POST", "/api/profile/", { university_id });
        const refreshed = await apiGetJson("/api/me/");
        const updatedProfile = refreshed.profile || {};
        if (currentUniEl)
          currentUniEl.textContent = updatedProfile.university
            ? updatedProfile.university.name
            : "No university selected";

        // Reload tasks for the selected university.
        if (updatedProfile.university) {
          const tasksRes = await apiGetJson("/api/tasks/");
          renderTasks(tasksRes.tasks);
        } else {
          const empty = el("tasks-empty");
          const list = el("task-list");
          if (list) clear(list);
          if (empty) empty.style.display = "block";
        }

        // Refresh reminder banner to match the selected university.
        const reminderRes = await apiGetJson("/api/reminders/today/");
        const banner = el("reminder-banner");
        const list = el("reminder-tasks");
        if (banner && list) {
          banner.style.display = reminderRes.should_show ? "block" : "none";
          if (reminderRes.should_show) {
            clear(list);
            for (const task of reminderRes.tasks) {
              const li = document.createElement("li");
              li.textContent = `${task.title} (due ${formatDueDate(task.due_date)})`;
              list.appendChild(li);
            }
          }
        }
      } catch (err) {
        console.error(err);
        showUiError(err.message || "Failed to save university");
      }
    });
  }

  if (profile.university) {
    // Load tasks
    const tasksRes = await apiGetJson("/api/tasks/");
    renderTasks(tasksRes.tasks);

    // Morning reminder
    const reminderRes = await apiGetJson("/api/reminders/today/");
    if (reminderRes.should_show) {
      const banner = el("reminder-banner");
      const list = el("reminder-tasks");
      const gotIt = el("reminder-got-it");
      if (banner && list) {
        clear(list);
        for (const task of reminderRes.tasks) {
          const li = document.createElement("li");
          li.textContent = `${task.title} (due ${formatDueDate(task.due_date)})`;
          list.appendChild(li);
        }
        banner.style.display = "block";
      }

      if (gotIt) {
        gotIt.addEventListener("click", async () => {
          try {
            await apiSendJson("POST", "/api/reminders/mark-shown/");
            const banner = el("reminder-banner");
            if (banner) banner.style.display = "none";
          } catch (err) {
            console.error(err);
            showUiError(err.message || "Failed to dismiss reminder");
          }
        });
      }
    }
  }

  // Add task
  const addForm = el("add-task-form");
  if (addForm) {
    addForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      try {
        const title = el("task-title").value;
        const due_date = el("task-due-date").value;
        await apiSendJson("POST", "/api/tasks/", { title, due_date });
        el("task-title").value = "";
        el("task-due-date").value = "";
        const refreshed = await apiGetJson("/api/tasks/");
        renderTasks(refreshed.tasks);
      } catch (err) {
        console.error(err);
        showUiError(err.message || "Failed to add task");
      }
    });
  }
}

async function bootSettings() {
  const form = el("profile-form");
  if (!form) return;

  const me = await apiGetJson("/api/me/");
  const universities = me.universities || [];
  const profile = me.profile || {};

  const uniSelect = el("university-select-settings");
  const timezone = el("timezone");
  const reminderEnabled = el("reminder-enabled");
  const morningHour = el("morning-hour");
  const errorBox = el("settings-error");
  const previewBtn = el("reminder-preview");
  const previewBox = el("reminder-preview-box");

  if (uniSelect) {
    clear(uniSelect);
    for (const uni of universities) {
      const opt = document.createElement("option");
      opt.value = uni.id;
      opt.textContent = uni.name;
      uniSelect.appendChild(opt);
    }
    if (profile.university) uniSelect.value = profile.university.id;
  }

  if (timezone) timezone.value = profile.timezone || "America/New_York";
  if (reminderEnabled) reminderEnabled.checked = !!profile.reminder_enabled;
  if (morningHour) morningHour.value = Number(profile.morning_hour ?? 8);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (errorBox) errorBox.style.display = "none";
    try {
      const payload = {
        university_id: Number(uniSelect.value),
        timezone: timezone.value,
        reminder_enabled: reminderEnabled.checked,
        morning_hour: (() => {
          const n = Number(morningHour.value);
          return Number.isFinite(n) ? n : 8;
        })(),
      };
      await apiSendJson("POST", "/api/profile/", payload);
      // Quick UX: show a simple confirmation message.
      if (errorBox) {
        errorBox.style.display = "block";
        errorBox.textContent = "Saved.";
        errorBox.className = "banner";
      }
    } catch (err) {
      if (errorBox) {
        errorBox.style.display = "block";
        errorBox.textContent = err.message || "Failed to save";
        errorBox.className = "banner banner-error";
      }
    }
  });

  if (previewBtn && previewBox) {
    previewBtn.addEventListener("click", async () => {
      try {
        const res = await apiGetJson("/api/reminders/today/");
        const tasks = res.tasks || [];
        if (tasks.length === 0) {
          previewBox.textContent = "Nothing due today for this university.";
          return;
        }
        previewBox.textContent = `Due today (${tasks.length}): ${tasks.map((t) => t.title).join("; ")}`;
      } catch (err) {
        console.error(err);
        showUiError(err.message || "Failed to load reminder preview");
      }
    });
  }
}

window.addEventListener("DOMContentLoaded", () => {
  // Decide which page we're on by checking which key elements exist.
  const hasAddTask = document.getElementById("add-task-form");
  const hasSettingsForm = document.getElementById("profile-form");
  if (hasSettingsForm) {
    bootSettings().catch((err) => {
      console.error(err);
      const box = el("settings-error");
      if (box) {
        box.style.display = "block";
        box.textContent = err.message || "Failed to load";
        box.className = "banner banner-error";
      }
      showUiError(err.message || "Failed to load");
    });
  } else if (hasAddTask) {
    bootHome().catch((err) => {
      console.error(err);
      showUiError(err.message || "Failed to load tasks");
    });
  }
});

