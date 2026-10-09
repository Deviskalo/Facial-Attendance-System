(function () {
  const video = document.getElementById("kiosk-video");
  const canvas = document.getElementById("kiosk-canvas");
  const toastEl = document.getElementById("kiosk-toast");
  const clockEl = document.getElementById("kiosk-clock");
  const cameraStatusEl = document.getElementById("kiosk-camera-status");
  const serviceStatusEl = document.getElementById("kiosk-service-status");
  const ctx = canvas.getContext("2d");
  const proto = location.protocol === "https:" ? "wss" : "ws";
  let socket;
  let cameraStream;
  let lastToast = 0;
  let sendBusy = false;
  let lastOverlay = { faces: [], frame_size: [1280, 720] };

  function setStatus(element, state, message) {
    element.className = "status-item " + state;
    element.replaceChildren(document.createElement("i"), document.createTextNode(message));
    element.firstChild.className = "status-dot";
  }

  function tickClock() {
    clockEl.textContent = new Date().toLocaleString();
  }
  setInterval(tickClock, 1000);
  tickClock();

  function showToast(toast) {
    if (!toast) return;
    const now = Date.now();
    if (now - lastToast < 2500 && toastEl.textContent === toast.message) return;
    lastToast = now;
    toastEl.textContent = toast.message;
    toastEl.className = "toast show " + (toast.type || "info");
    if (window.speechSynthesis) {
      const utter = new SpeechSynthesisUtterance(toast.message);
      utter.rate = 1;
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utter);
    }
    setTimeout(() => toastEl.classList.remove("show"), 3200);
  }

  function connect() {
    setStatus(serviceStatusEl, "warning", "Connecting to attendance service");
    socket = new WebSocket(`${proto}://${location.host}/ws/kiosk`);
    socket.binaryType = "arraybuffer";
    socket.onopen = () => {
      setStatus(serviceStatusEl, "ready", "Attendance service connected");
    };
    socket.onerror = () => {
      setStatus(serviceStatusEl, "error", "Attendance service connection error");
    };
    socket.onclose = () => {
      setStatus(serviceStatusEl, "error", "Service disconnected · reconnecting");
      setTimeout(connect, 1200);
    };
    socket.onmessage = (ev) => {
      const data = JSON.parse(ev.data);
      lastOverlay = data;
      if (data.toast) showToast(data.toast);
    };
  }

  function color(name) {
    if (name === "green") return "#22c55e";
    if (name === "red") return "#ef4444";
    return "#eab308";
  }

  function draw() {
    const vw = video.videoWidth || 1280;
    const vh = video.videoHeight || 720;
    if (canvas.width !== vw) canvas.width = vw;
    if (canvas.height !== vh) canvas.height = vh;
    ctx.save();
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();
    const data = lastOverlay;
    const fw = (data.frame_size && data.frame_size[0]) || canvas.width;
    const fh = (data.frame_size && data.frame_size[1]) || canvas.height;
    const sx = canvas.width / fw;
    const sy = canvas.height / fh;
    (data.faces || []).forEach((face) => {
      const [x1, y1, x2, y2] = face.bbox;
      const mirroredX1 = canvas.width - x2 * sx;
      const mirroredX2 = canvas.width - x1 * sx;
      ctx.strokeStyle = color(face.color);
      ctx.lineWidth = 4;
      ctx.strokeRect(mirroredX1, y1 * sy, mirroredX2 - mirroredX1, (y2 - y1) * sy);
      if (face.name) {
        ctx.fillStyle = color(face.color);
        ctx.font = "24px Segoe UI";
        ctx.fillText(face.name, mirroredX1, Math.max(28, y1 * sy - 10));
      }
    });
  }

  async function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("Camera access requires HTTPS or localhost in a supported browser.");
    }
    setStatus(cameraStatusEl, "warning", "Starting camera");
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "user" },
      audio: false,
    });
    video.srcObject = cameraStream;
    await video.play();
    setStatus(cameraStatusEl, "ready", "Camera ready");
    cameraStream.getVideoTracks().forEach((track) => {
      track.addEventListener("ended", () => {
        setStatus(cameraStatusEl, "error", "Camera disconnected");
      });
    });
    const scratch = document.createElement("canvas");
    setInterval(() => {
      if (!socket || socket.readyState !== 1 || sendBusy) return;
      if (!video.videoWidth) return;
      scratch.width = 640;
      scratch.height = Math.round((video.videoHeight / video.videoWidth) * 640) || 360;
      scratch.getContext("2d").drawImage(video, 0, 0, scratch.width, scratch.height);
      scratch.toBlob(
        (blob) => {
          if (!blob || socket.readyState !== 1) return;
          sendBusy = true;
          blob.arrayBuffer().then((buf) => {
            socket.send(buf);
            sendBusy = false;
          }).catch(() => { sendBusy = false; });
        },
        "image/jpeg",
        0.7
      );
    }, 280);
    const loop = () => {
      if (video.videoWidth) draw();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  connect();
  startCamera().catch((err) => {
    setStatus(cameraStatusEl, "error", "Camera unavailable");
    toastEl.textContent = "Camera permission required: " + err.message;
    toastEl.className = "toast show late";
  });
})();
