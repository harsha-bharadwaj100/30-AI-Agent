document.addEventListener("DOMContentLoaded", () => {
  // --- UI Elements ---
  const startRecordingBtn = document.getElementById("start-recording");
  const stopRecordingBtn = document.getElementById("stop-recording");
  const playbackAudio = document.getElementById("playback-audio");
  const statusDiv = document.getElementById("status");

  // --- State Management ---
  let mediaRecorder;
  let recordedChunks = [];
  let sessionId = null;

  // --- Initialize Session ---
  function initializeSession() {
    const params = new URLSearchParams(window.location.search);
    if (params.has("session_id")) {
      sessionId = params.get("session_id");
    } else {
      // Generate a simple unique ID for the session
      sessionId =
        Date.now().toString(36) + Math.random().toString(36).substring(2);
      // Update URL without reloading the page
      window.history.pushState(
        { sessionId },
        `Session: ${sessionId}`,
        `?session_id=${sessionId}`
      );
    }
    console.log("Session ID:", sessionId);
  }

  initializeSession();

  // --- Core Agent Interaction Function ---
  async function interactWithAgent(audioBlob) {
    statusDiv.textContent = "Thinking...";
    const formData = new FormData();
    formData.append("audio", audioBlob, `recording-${Date.now()}.webm`);

    try {
      const response = await fetch(`/agent/chat/${sessionId}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to process audio.");
      }

      statusDiv.textContent = "Agent is responding...";
      const result = await response.json();

      playbackAudio.src = result.audio_url;
      playbackAudio.play();
    } catch (error) {
      console.error("Agent Interaction Error:", error);
      statusDiv.textContent = `Error: ${error.message}. Press "Start" to try again.`;
      startRecordingBtn.disabled = false;
      stopRecordingBtn.disabled = true;
    }
  }

  // --- Event Handlers ---
  startRecordingBtn.addEventListener("click", async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      recordedChunks = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordedChunks.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(recordedChunks, { type: "audio/webm" });
        interactWithAgent(blob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.start();
      startRecordingBtn.disabled = true;
      stopRecordingBtn.disabled = false;
      statusDiv.textContent = "Listening...";
    } catch (error) {
      console.error("Microphone access error:", error);
      statusDiv.textContent = "Could not access microphone.";
    }
  });

  stopRecordingBtn.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      startRecordingBtn.disabled = false;
      stopRecordingBtn.disabled = true;
      statusDiv.textContent = "Processing your voice...";
    }
  });

  // --- Continuous Conversation Loop ---
  playbackAudio.addEventListener("ended", () => {
    statusDiv.textContent = "Response finished. Listening for your reply...";
    // Programmatically click the start button to begin listening again
    startRecordingBtn.click();
  });
});
