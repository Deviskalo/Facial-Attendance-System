(function () {
  const video = document.getElementById("kiosk-video");
  const canvas = document.getElementById("kiosk-canvas");
  const overlaysEl = document.getElementById("kiosk-overlays");
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
      updateOverlays();
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
    updateOverlays();
  }

  function updateOverlays() {
    const data = lastOverlay;
    const fw = (data.frame_size && data.frame_size[0]) || canvas.width;
    const fh = (data.frame_size && data.frame_size[1]) || canvas.height;
    const bounds = overlaysEl.getBoundingClientRect();
    if (!bounds.width || !bounds.height || !canvas.width || !canvas.height) return;
    const scale = Math.max(bounds.width / canvas.width, bounds.height / canvas.height);
    const offsetX = (bounds.width - canvas.width * scale) / 2;
    const offsetY = (bounds.height - canvas.height * scale) / 2;
    const boxes = (data.faces || []).map((face) => {
      const [x1, y1, x2, y2] = face.bbox;
      const box = document.createElement("div");
      const faceColor = color(face.color);
      const mirroredLeft = canvas.width - x2 * canvas.width / fw;
      box.className = "face-box";
      box.style.setProperty("--face-color", faceColor);
      box.style.left = `${offsetX + mirroredLeft * scale}px`;
      box.style.top = `${offsetY + y1 * canvas.height / fh * scale}px`;
      box.style.width = `${(x2 - x1) * canvas.width / fw * scale}px`;
      box.style.height = `${(y2 - y1) * canvas.height / fh * scale}px`;
      if (face.name) {
        const label = document.createElement("span");
        label.className = "face-box-label";
        label.textContent = face.name;
        box.appendChild(label);
      }
      return box;
    });
    overlaysEl.replaceChildren(...boxes);
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
