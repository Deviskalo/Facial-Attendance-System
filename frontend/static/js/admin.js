async function loadLogs() {
  const params = new URLSearchParams();
  const start = document.getElementById("start_date")?.value;
  const end = document.getElementById("end_date")?.value;
  const department = document.getElementById("department")?.value;
  const status = document.getElementById("status_filter")?.value;
  if (start) params.set("start_date", start);
  if (end) params.set("end_date", end);
  if (department) params.set("department", department);
  if (status) params.set("status_filter", status);
  const res = await fetch("/api/logs?" + params.toString());
  const rows = await res.json();
  const body = document.getElementById("logs-body");
  if (!body) return;
  body.innerHTML = rows
    .map(
      (r) => `<tr>
        <td>${r.timestamp}</td>
        <td>${r.employee_id}</td>
        <td>${r.name}</td>
        <td>${r.department}</td>
        <td>${r.event_type}</td>
        <td>${r.status}</td>
        <td>${r.confidence_score ?? ""}</td>
        <td>
          <button class="btn secondary" onclick="editLog(${r.id}, '${r.timestamp}')">Edit time</button>
        </td>
      </tr>`
    )
    .join("");
}

async function loadLogAudit() {
  const body = document.getElementById("log-audit-body");
  if (!body) return;
  const response = await fetch("/api/logs/audit");
  if (!response.ok) {
    throw new Error("Could not load attendance correction history.");
  }
  const rows = await response.json();
  body.replaceChildren();
  const actionLabels = {
    edit: "Edited attendance",
    manual_present: "Marked present",
    manual_absence: "Cleared attendance",
  };
  rows.forEach((record) => {
    const row = document.createElement("tr");
    [
      record.changed_at,
      actionLabels[record.action] || record.action,
      `${record.employee_id}${record.name ? " · " + record.name : ""}`,
      record.actor,
      record.reason,
    ].forEach((value) => {
      const cell = document.createElement("td");
      cell.textContent = value || "";
      row.appendChild(cell);
    });
    const detailsCell = document.createElement("td");
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = "View changes";
    const pre = document.createElement("pre");
    const before = record.before_data ? JSON.parse(record.before_data) : null;
    const after = record.after_data ? JSON.parse(record.after_data) : null;
    pre.textContent = [
      before ? "Before: " + JSON.stringify(before, null, 2) : "Before: (none)",
      after ? "After: " + JSON.stringify(after, null, 2) : "After: (record removed)",
    ].join("\n");
    details.append(summary, pre);
    detailsCell.appendChild(details);
    row.appendChild(detailsCell);
    body.appendChild(row);
  });
}

async function refreshLogs() {
  await Promise.all([loadLogs(), loadLogAudit()]);
}

async function editLog(id, current) {
  const timestamp = prompt("New timestamp (YYYY-MM-DD HH:MM:SS)", current);
  if (!timestamp) return;
  const reason = prompt("Reason for this correction (required):", "");
  if (!reason || !reason.trim()) {
    alert("A reason is required to edit an attendance record.");
    return;
  }
  const response = await fetch("/api/logs/" + id, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ timestamp, reason: reason.trim() }),
  });
  if (!response.ok) {
    const error = await response.json();
    alert(error.detail || "Could not update the attendance record.");
    return;
  }
  await refreshLogs();
}

async function manualEntry() {
  const employee_id = document.getElementById("manual_emp").value.trim();
  const action = document.getElementById("manual_action").value;
  const reason = document.getElementById("correction_reason").value.trim();
  if (!reason) {
    alert("Enter a reason for this attendance correction.");
    document.getElementById("correction_reason").focus();
    return;
  }
  const payload = { employee_id, action, reason };
  if (action === "present") {
    payload.event_type = "CHECK_IN";
    payload.status = "MANUAL";
  }
  const response = await fetch("/api/logs/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const error = await response.json();
    alert(error.detail || "Could not apply the attendance correction.");
    return;
  }
  document.getElementById("correction_reason").value = "";
  await refreshLogs();
}

function exportLogs(fmt) {
  const params = new URLSearchParams();
  const start = document.getElementById("start_date")?.value;
  const end = document.getElementById("end_date")?.value;
  const department = document.getElementById("department")?.value;
  const status = document.getElementById("status_filter")?.value;
  if (start) params.set("start_date", start);
  if (end) params.set("end_date", end);
  if (department) params.set("department", department);
  if (status) params.set("status_filter", status);
  params.set("fmt", fmt);
  window.location.href = "/api/logs/export?" + params.toString();
}

function exportAudit(fmt) {
  window.location.href = "/api/logs/audit/export?" + new URLSearchParams({ fmt });
}

async function deleteEmployee(id) {
  if (!confirm("Delete " + id + "?")) return;
  await fetch("/api/employees/" + id, { method: "DELETE" });
  window.location.reload();
}

function connectActivity() {
  const list = document.getElementById("activity-list");
  if (!list) return;
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/activity`);
  const add = (event) => {
    const div = document.createElement("div");
    div.className = "item";
    div.innerHTML = `<span class="tag ${event.kind}">${event.kind}</span> ${event.ts || ""} — ${event.message} ${event.name ? "(" + event.name + ")" : ""}`;
    list.prepend(div);
  };
  ws.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    if (data.type === "history") data.events.forEach(add);
    if (data.type === "event") add(data.event);
  };
}

document.addEventListener("DOMContentLoaded", () => {
  if (document.getElementById("logs-body")) {
    refreshLogs().catch((error) => alert(error.message));
  }
  connectActivity();
});
