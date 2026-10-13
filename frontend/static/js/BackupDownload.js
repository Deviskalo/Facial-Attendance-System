(function () {
  document.querySelectorAll('a[href="/api/backup"]').forEach((link) => {
    const status = document.createElement("span");
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    link.insertAdjacentElement("afterend", status);

    link.addEventListener("click", async (event) => {
      if (!window.pywebview) return;
      event.preventDefault();

      const api = window.pywebview.api;
      if (!api || typeof api.save_backup !== "function") {
        status.textContent = "The desktop save dialog is not ready. Try again.";
        return;
      }
      if (link.dataset.busy === "true") return;

      link.dataset.busy = "true";
      status.textContent = "Preparing backup...";
      try {
        const response = await fetch("/api/backup/export", {
          credentials: "same-origin",
        });
        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || "Could not prepare the backup.");
        }

        const savedName = await api.save_backup(result.ticket);
        status.textContent = savedName
          ? `Saved ${savedName}.`
          : "Backup save canceled.";
      } catch (error) {
        status.textContent = error.message || "Could not save the backup.";
      } finally {
        delete link.dataset.busy;
      }
    });
  });
})();
