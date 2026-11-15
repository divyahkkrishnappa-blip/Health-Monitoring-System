(() => {
  let stream = null;
  document.addEventListener("DOMContentLoaded", () => {
    const video = document.getElementById("camera-video");
    const start = document.querySelector("[data-camera-start]");
    const stop = document.querySelector("[data-camera-stop]");
    const status = document.querySelector("[data-camera-status]");
    const placeholder = document.querySelector("[data-camera-placeholder]");
    const live = document.querySelector("[data-camera-live]");
    if (!video || !start || !stop) return;
    const setStatus = (message) => { status.textContent = message; };
    const stopCamera = () => {
      if (stream) stream.getTracks().forEach((track) => track.stop());
      stream = null;
      video.srcObject = null;
      video.style.display = "none";
      placeholder.hidden = false;
      live.hidden = true;
      start.disabled = false;
      stop.disabled = true;
      setStatus("Camera stopped");
    };
    start.addEventListener("click", async () => {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setStatus("Camera access is unavailable in this browser or context. Use localhost or HTTPS.");
        return;
      }
      start.disabled = true;
      setStatus("Waiting for camera permission…");
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        video.srcObject = stream;
        video.style.display = "block";
        placeholder.hidden = true;
        live.hidden = false;
        stop.disabled = false;
        setStatus("Camera preview active. No measurements are being taken.");
      } catch (error) {
        start.disabled = false;
        if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") setStatus("Camera permission was denied. Allow access in browser settings to preview.");
        else if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") setStatus("No camera was found on this device.");
        else setStatus(`Unable to start camera: ${error.message}`);
      }
    });
    stop.addEventListener("click", stopCamera);
    window.addEventListener("pagehide", stopCamera);
  });
})();
