document.addEventListener("DOMContentLoaded", () => {
  // --- UI Elements ---
  const startRecordingBtn = document.getElementById("start-recording");
  const stopRecordingBtn = document.getElementById("stop-recording");
  const playbackAudio = document.getElementById("playback-audio");
  const statusDiv = document.getElementById("status");
  const errorDiv = document.getElementById("error-message");

  // --- State Management ---
  let mediaRecorder;
  let recordedChunks = [];
  let sessionId = null;
  let isProcessing = false;

  // --- Error Display Functions ---
  function showError(message, isTemporary = true) {
    if (errorDiv) {
      errorDiv.textContent = message;
      errorDiv.style.display = "block";
      errorDiv.className = "error-message show";

      if (isTemporary) {
        setTimeout(() => {
          hideError();
        }, 5000);
      }
    }
    console.error("Application Error:", message);
  }

  function hideError() {
    if (errorDiv) {
      errorDiv.style.display = "none";
      errorDiv.className = "error-message";
    }
  }

  function updateStatus(message, isError = false) {
    if (statusDiv) {
      statusDiv.textContent = message;
      statusDiv.className = isError ? "status error" : "status";
    }
  }

  // --- FIXED: Button State Management ---
  function enableRecordingControls() {
    startRecordingBtn.disabled = false;
    stopRecordingBtn.disabled = true;
    isProcessing = false;
    updateStatus("Ready to listen...");
  }

  function disableAllControls() {
    startRecordingBtn.disabled = true;
    stopRecordingBtn.disabled = true;
  }

  // --- Initialize Session ---
  function initializeSession() {
    const params = new URLSearchParams(window.location.search);
    if (params.has("session_id")) {
      sessionId = params.get("session_id");
    } else {
      sessionId =
        Date.now().toString(36) + Math.random().toString(36).substring(2);
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
    if (isProcessing) {
      showError("Please wait for the current request to complete.");
      return;
    }

    isProcessing = true;
    disableAllControls();
    hideError();
    updateStatus("Processing your request...");

    const formData = new FormData();
    formData.append("audio", audioBlob, `recording-${Date.now()}.webm`);

    try {
      updateStatus("Connecting to AI services...");
      const response = await fetch(`/agent/chat/${sessionId}`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage =
          errorData.detail || `Server error (${response.status})`;
        throw new Error(errorMessage);
      }

      const result = await response.json();

      if (result.error) {
        showError(result.message, false);
        updateStatus("AI service temporarily unavailable", true);

        if (result.audio_url) {
          playbackAudio.src = result.audio_url;
          playbackAudio.play().catch((e) => {
            console.warn("Could not play fallback audio:", e);
          });
        }
      } else if (result.audio_url) {
        updateStatus("AI is responding...");
        playbackAudio.src = result.audio_url;

        playbackAudio.play().catch((playError) => {
          console.warn("Audio playback failed:", playError);
          showError(
            "I generated a response but couldn't play the audio. Please check your speakers."
          );
          enableRecordingControls(); // Re-enable if playback fails
        });
      } else {
        showError("Received an unexpected response from the server.");
        enableRecordingControls();
      }
    } catch (error) {
      console.error("Agent Interaction Error:", error);
      showError(`Connection error: ${error.message}`);
      enableRecordingControls();
    }
  }

  // --- Microphone Access ---
  async function requestMicrophoneAccess() {
    try {
      return await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100,
        },
      });
    } catch (error) {
      let errorMessage = "Could not access microphone. ";

      if (error.name === "NotAllowedError") {
        errorMessage += "Please allow microphone access and refresh the page.";
      } else if (error.name === "NotFoundError") {
        errorMessage += "No microphone found. Please connect a microphone.";
      } else {
        errorMessage += "Please check your microphone settings.";
      }

      throw new Error(errorMessage);
    }
  }

  // --- Event Handlers ---
  startRecordingBtn.addEventListener("click", async () => {
    try {
      hideError();
      updateStatus("Requesting microphone access...");

      const stream = await requestMicrophoneAccess();

      mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      });
      recordedChunks = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordedChunks.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(recordedChunks, { type: "audio/webm" });

        if (blob.size < 1000) {
          showError(
            "Recording seems too short. Please try speaking for longer."
          );
          enableRecordingControls();
          return;
        }

        interactWithAgent(blob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.onerror = (error) => {
        console.error("MediaRecorder error:", error);
        showError("Recording failed. Please try again.");
        stream.getTracks().forEach((track) => track.stop());
        enableRecordingControls();
      };

      mediaRecorder.start();
      startRecordingBtn.disabled = true;
      stopRecordingBtn.disabled = false;
      updateStatus("Listening...");
    } catch (error) {
      console.error("Recording start error:", error);
      showError(error.message);
      enableRecordingControls();
    }
  });

  stopRecordingBtn.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      disableAllControls();
      updateStatus("Processing...");
    }
  });

  // --- FIXED: Automatic Conversation Loop ---
  playbackAudio.addEventListener("ended", () => {
    updateStatus("Response finished. Ready for your next message...");
    // Automatically re-enable recording after the AI finishes speaking
    setTimeout(() => {
      enableRecordingControls();
      // Automatically start listening for the next turn
      setTimeout(() => {
        if (!isProcessing) {
          startRecordingBtn.click();
        }
      }, 500);
    }, 1000);
  });

  // --- Connection Status Monitoring ---
  window.addEventListener("online", () => {
    hideError();
    if (!isProcessing) {
      enableRecordingControls();
    }
  });

  window.addEventListener("offline", () => {
    showError("You are offline. Please check your internet connection.", false);
    updateStatus("Offline", true);
    disableAllControls();
  });

  // --- Initial Status ---
  enableRecordingControls();
  updateStatus('Press "Start" to begin conversation.');
});
