document.addEventListener("DOMContentLoaded", () => {
  const startBtn = document.getElementById("start-streaming");
  const stopBtn = document.getElementById("stop-streaming");
  const statusDiv = document.getElementById("status");
  const transcriptDiv = document.getElementById("transcript");

  let mediaRecorder;
  let websocket;
  let audioContext;
  let processor;
  let stream;

  // --- WebSocket and Audio Processing Logic ---
  const setupWebSocket = () => {
    websocket = new WebSocket(
      `ws://${window.location.host}/ws/stream-for-transcription`
    );

    websocket.onopen = () => {
      statusDiv.textContent = "Status: Connected. Start speaking!";
      transcriptDiv.innerHTML = "<p><em>Listening...</em></p>";
    };

    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.transcript) {
        transcriptDiv.innerHTML = `<p>${data.transcript}</p>`;
      }
    };

    websocket.onclose = () => {
      statusDiv.textContent = "Status: Disconnected";
    };

    websocket.onerror = (error) => {
      console.error("WebSocket Error:", error);
      statusDiv.textContent = "Status: Error connecting.";
    };
  };

  const startStreaming = async () => {
    try {
      startBtn.disabled = true;
      stopBtn.disabled = false;

      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000, // Set sample rate to 16kHz for AssemblyAI
      });

      const source = audioContext.createMediaStreamSource(stream);
      processor = audioContext.createScriptProcessor(1024, 1, 1);

      source.connect(processor);
      processor.connect(audioContext.destination);

      processor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        // Convert to 16-bit PCM
        const pcmData = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          let s = Math.max(-1, Math.min(1, inputData[i]));
          pcmData[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        if (websocket && websocket.readyState === WebSocket.OPEN) {
          websocket.send(pcmData.buffer);
        }
      };

      setupWebSocket();
    } catch (error) {
      console.error("Error starting stream:", error);
      statusDiv.textContent = "Error: Could not access microphone.";
      startBtn.disabled = false;
      stopBtn.disabled = true;
    }
  };

  const stopStreaming = () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
    }
    if (processor) {
      processor.disconnect();
    }
    if (audioContext) {
      audioContext.close();
    }
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      websocket.close();
    }

    startBtn.disabled = false;
    stopBtn.disabled = true;
    statusDiv.textContent = "Status: Disconnected";
  };

  // --- Event Listeners ---
  startBtn.addEventListener("click", startStreaming);
  stopBtn.addEventListener("click", stopStreaming);
});
