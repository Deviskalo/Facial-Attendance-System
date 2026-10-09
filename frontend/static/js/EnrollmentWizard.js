(function () {
  const video = document.getElementById("enroll-video");
  const canvas = document.getElementById("enroll-canvas");
  const ctx = canvas.getContext("2d");
  const captureBtn = document.getElementById("capture-btn");
  const finishBtn = document.getElementById("finish-btn");
  const qualityEl = document.getElementById("quality");
  const guidanceEl = document.getElementById("quality-guidance");
  const progressEl = document.getElementById("enroll-progress");
  const progressLabelEl = document.getElementById("enroll-progress-label");
  const statusEl = document.getElementById("enroll-status");
  const poses = JSON.parse(document.getElementById("pose-data").textContent);
  let index = 0;
  const captured = new Set();
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${proto}://${location.host}/ws/enroll`);
  const scratch = document.createElement("canvas");
  const scratchContext = scratch.getContext("2d");
  let cameraReady = false;
  let lastQualityOk = false;
  let analysisInFlight = false;
  let capturePending = false;
  let analyzeTimer;
  let latestFace = null;
  let latestFrameSize = null;

  function currentPose() {
    return poses[index];
  }

  function updateControls() {
    const connected = socket.readyState === WebSocket.OPEN;
    captureBtn.disabled =
      !connected || !cameraReady || !lastQualityOk || capturePending;
    finishBtn.disabled =
      !connected || capturePending || captured.size !== poses.length;
  }

  function renderSteps() {
    poses.forEach((pose, i) => {
      const el = document.getElementById("step-" + pose.id);
      el.classList.toggle("current", i === index);
      el.classList.toggle("done", captured.has(pose.id));
    });
    const pose = currentPose();
    if (pose) {
      captureBtn.textContent = "Capture " + pose.label;
      document.getElementById("pose-hint").textContent = pose.hint;
    }
    progressEl.value = captured.size;
    progressLabelEl.textContent = `${captured.size} of ${poses.length} poses captured`;
    updateControls();
  }

  function grabJpeg() {
    scratch.width = 640;
    scratch.height = Math.round((video.videoHeight / video.videoWidth) * 640) || 360;
    scratchContext.drawImage(video, 0, 0, scratch.width, scratch.height);
    return scratch.toDataURL("image/jpeg", 0.85);
  }

  function renderPreview() {
    if (!cameraReady || !video.videoWidth) {
      requestAnimationFrame(renderPreview);
      return;
    }
    if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    if (latestFace && latestFrameSize) {
      const sx = canvas.width / latestFrameSize[0];
      const sy = canvas.height / latestFrameSize[1];
      const [x1, y1, x2, y2] = latestFace;
      ctx.strokeStyle = lastQualityOk ? "#22c55e" : "#eab308";
      ctx.lineWidth = 4;
      ctx.strokeRect(x1 * sx, y1 * sy, (x2 - x1) * sx, (y2 - y1) * sy);
    }
    requestAnimationFrame(renderPreview);
  }

  function scheduleAnalyze(delay = 400) {
    clearTimeout(analyzeTimer);
    analyzeTimer = setTimeout(sendAnalyze, delay);
  }

  function sendAnalyze() {
    if (
      socket.readyState !== WebSocket.OPEN ||
      !cameraReady ||
      !video.videoWidth ||
      analysisInFlight ||
      capturePending
    ) {
      return;
    }
    analysisInFlight = true;
    try {
      socket.send(JSON.stringify({ type: "analyze", image: grabJpeg() }));
    } catch (err) {
      analysisInFlight = false;
      statusEl.textContent = "Could not analyze the camera frame: " + err.message;
      scheduleAnalyze();
    }
  }

  socket.onopen = () => {
    statusEl.textContent = "Connected to enrollment service. Starting camera...";
    updateControls();
  };

  socket.onerror = () => {
    statusEl.textContent = "Enrollment connection error. Check the server and refresh this page.";
  };

  socket.onclose = (event) => {
    lastQualityOk = false;
    capturePending = false;
    clearTimeout(analyzeTimer);
    updateControls();
    statusEl.textContent =
      event.code === 1008
        ? "Enrollment connection rejected. Refresh the page and sign in again."
        : `Enrollment connection closed (${event.code}). Check the server and refresh this page.`;
  };

  socket.onmessage = (ev) => {
    const data = JSON.parse(ev.data);
    if (data.type === "analyze") {
      analysisInFlight = false;
      if (!data.ok) {
        lastQualityOk = false;
        latestFace = null;
        const issue = document.createElement("li");
        issue.textContent = data.error || "Frame analysis failed.";
        qualityEl.replaceChildren(issue);
        guidanceEl.textContent = issue.textContent;
        guidanceEl.className = "quality-guidance error";
        updateControls();
        scheduleAnalyze();
        return;
      }
      lastQualityOk = !!(data.quality && data.quality.ok);
      latestFace = data.face && data.face.bbox;
      latestFrameSize = data.frame_size;
      const issues = (data.quality && data.quality.issues) || [];
      qualityEl.innerHTML = issues.length
        ? issues.map((i) => "<li>" + i + "</li>").join("")
        : "<li>Ready to capture.</li>";
      guidanceEl.textContent = issues.length
        ? issues.join(" ")
        : captured.size === poses.length
          ? "All poses captured. Enter the person's details and save."
          : `Good to go. Capture ${currentPose().label} when ready.`;
      guidanceEl.className = "quality-guidance " + (issues.length ? "warning" : "ready");
      updateControls();
      scheduleAnalyze();
    } else if (data.type === "capture") {
      capturePending = false;
      if (data.ok) {
        captured.add(data.pose);
        if (index < poses.length - 1) index += 1;
        statusEl.textContent = "Captured " + data.pose + ".";
        renderSteps();
      } else {
        statusEl.textContent = data.error || "Capture failed.";
        if (data.quality && data.quality.issues && data.quality.issues.length) {
          guidanceEl.textContent = data.quality.issues.join(" ");
          guidanceEl.className = "quality-guidance warning";
        }
        updateControls();
      }
      scheduleAnalyze(0);
    } else if (data.type === "finalize") {
      if (data.ok) {
        window.location.href = "/admin/people";
      } else {
        statusEl.textContent = data.error || "Could not save this person.";
      }
    } else if (!data.ok && data.error) {
      statusEl.textContent = data.error;
    }
  };

  captureBtn.addEventListener("click", () => {
    const pose = currentPose();
    if (!pose) {
      statusEl.textContent = "No enrollment pose is selected.";
      return;
    }
    if (socket.readyState !== WebSocket.OPEN) {
      statusEl.textContent = "Enrollment service is not connected. Refresh this page and try again.";
      updateControls();
      return;
    }
    if (!cameraReady || !video.videoWidth) {
      statusEl.textContent = "Camera is not ready. Check camera access and try again.";
      updateControls();
      return;
    }
    try {
      capturePending = true;
      clearTimeout(analyzeTimer);
      updateControls();
      socket.send(JSON.stringify({ type: "capture", pose: pose.id, image: grabJpeg() }));
      statusEl.textContent = "Capturing " + pose.label + "...";
    } catch (err) {
      capturePending = false;
      updateControls();
      statusEl.textContent = "Could not send the photo: " + err.message;
    }
  });

  finishBtn.addEventListener("click", () => {
    if (socket.readyState !== WebSocket.OPEN) {
      statusEl.textContent = "Enrollment service is not connected. Refresh this page and try again.";
      updateControls();
      return;
    }
    try {
      socket.send(
        JSON.stringify({
          type: "finalize",
          name: document.getElementById("name").value,
          department: document.getElementById("department").value,
          employee_id: document.getElementById("employee_id").value,
        })
      );
    } catch (err) {
      statusEl.textContent = "Could not save the person: " + err.message;
    }
  });

  const getUserMedia = navigator.mediaDevices && navigator.mediaDevices.getUserMedia;
  if (!getUserMedia) {
    statusEl.textContent = "Camera access requires HTTPS or localhost in a supported browser.";
    guidanceEl.textContent = statusEl.textContent;
    guidanceEl.className = "quality-guidance error";
  } else {
    getUserMedia
      .call(navigator.mediaDevices, {
        video: {
          width: { ideal: 640 },
          height: { ideal: 480 },
          facingMode: "user",
        },
        audio: false,
      })
      .then((stream) => {
        video.srcObject = stream;
        return video.play();
      })
      .then(() => {
        cameraReady = true;
        updateControls();
        requestAnimationFrame(renderPreview);
        scheduleAnalyze(0);
      })
      .catch((err) => {
        statusEl.textContent = "Camera error: " + err.message;
        guidanceEl.textContent = statusEl.textContent;
        guidanceEl.className = "quality-guidance error";
      });
  }

  renderSteps();
})();
