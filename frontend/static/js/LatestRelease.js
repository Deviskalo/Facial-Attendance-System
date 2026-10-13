(function () {
  const title = document.getElementById("release-title");
  const description = document.getElementById("release-description");
  const download = document.getElementById("release-download");
  const notes = document.getElementById("release-notes");
  const apiUrl =
    "https://api.github.com/repos/Deviskalo/Facial-Attendance-System/releases/latest";

  async function showLatestRelease() {
    try {
      const response = await fetch(apiUrl, {
        headers: { Accept: "application/vnd.github+json" },
      });
      if (!response.ok) {
        if (response.status === 404) {
          title.textContent = "No desktop installer is published yet.";
          description.textContent =
            "When a signed installer is attached to a published GitHub release, its direct download link will appear here.";
          return;
        }
        throw new Error(`GitHub returned HTTP ${response.status}.`);
      }

      const release = await response.json();
      const installer = (release.assets || []).find((asset) =>
        /setup.*\.exe$/i.test(asset.name)
      );
      if (!installer || !installer.browser_download_url) {
        title.textContent = "No Windows installer is attached to the latest release.";
        description.textContent =
          "Check the release notes for availability, or see the publishing instructions below.";
        notes.href = release.html_url;
        notes.textContent = "View latest release";
        return;
      }

      title.textContent = `${release.name || release.tag_name} is available.`;
      description.textContent = `Download the Windows installer (${installer.name}). Review the release notes for version details and requirements.`;
      download.href = installer.browser_download_url;
      download.download = installer.name;
      download.classList.remove("hidden");
      notes.href = release.html_url;
      notes.textContent = "Release notes";
    } catch (error) {
      title.textContent = "Could not check GitHub for the latest installer.";
      description.textContent =
        "Check your internet connection or open the GitHub releases page.";
      console.error("Could not load the latest desktop release:", error);
    }
  }

  showLatestRelease();
})();
