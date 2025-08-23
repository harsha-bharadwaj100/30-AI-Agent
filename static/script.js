let mediaRecorder;
let ws;
let stream;

const startBtn = document.getElementById("start-recording");
const stopBtn = document.getElementById("stop-recording");

startBtn.addEventListener("click", async () => {
  startBtn.disabled = true;
  stopBtn.disabled = false;
  stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);

  ws = new WebSocket(`ws://${window.location.host}/ws/stream-audio`);

  mediaRecorder.ondataavailable = async (event) => {
    if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
      const arrayBuffer = await event.data.arrayBuffer();
      ws.send(arrayBuffer);
    }
  };

  mediaRecorder.start(250); // Send audio chunks every 250ms

  ws.onopen = () => {
    console.log("WebSocket connection established!");
  };

  ws.onclose = () => {
    console.log("WebSocket closed!");
    mediaRecorder.stop();
    stream.getTracks().forEach((track) => track.stop());
    startBtn.disabled = false;
    stopBtn.disabled = true;
  };
});

stopBtn.addEventListener("click", () => {
  stopBtn.disabled = true;
  startBtn.disabled = false;
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.close();
  }
  if (stream) {
    stream.getTracks().forEach((track) => track.stop());
  }
});
