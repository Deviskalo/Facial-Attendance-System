(function () {
  const form = document.getElementById("settings-form");
  const statusEl = document.getElementById("settings-status");
  const slider = document.getElementById("matching_threshold");
  const sliderVal = document.getElementById("threshold-val");
  const video = document.getElementById("calib-video");
  const resultEl = document.getElementById("calib-result");

  slider.addEventListener("input", () => {
    sliderVal.textContent = Number(slider.value).toFixed(2);
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(form).entries());
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const result = await res.json();
    statusEl.textContent = res.ok
      ? "Settings saved."
      : result.detail || "Could not save settings.";
  });

  async function loopCalib() {
    if (!video.videoWidth) return requestAnimationFrame(loopCalib);
    const scratch = document.createElement("canvas");
    scratch.width = 480;
    scratch.height = Math.round((video.videoHeight / video.videoWidth) * 480) || 270;
    scratch.getContext("2d").drawImage(video, 0, 0, scratch.width, scratch.height);
    const image = scratch.toDataURL("image/jpeg", 0.7);
    try {
      const res = await fetch("/api/preview-match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image }),
      });
      const data = await res.json();
      if (!data.matches || !data.matches.length) {
        resultEl.textContent = (data.quality && data.quality.issues && data.quality.issues[0]) || "No enrolled matches yet.";
      } else {
        resultEl.innerHTML = data.matches
          .map((m) => {
            const flag = m.would_match ? "MATCH" : "no match";
            return `${m.name} — distance ${m.distance.toFixed(3)} (${flag})`;
          })
          .join("<br>");
      }
    } catch (err) {
      resultEl.textContent = "Preview unavailable.";
    }
    setTimeout(loopCalib, 700);
  }

  if (video) {
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: false })
      .then((stream) => {
        video.srcObject = stream;
        return video.play();
      })
      .then(() => loopCalib())
      .catch(() => {
        resultEl.textContent = "Enable the camera to preview matching.";
      });
  }
})();
