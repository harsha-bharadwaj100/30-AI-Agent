document.addEventListener("DOMContentLoaded", () => {
  // UI Elements
  const voiceButton = document.getElementById("voice-button");
  const buttonIcon = document.getElementById("button-icon");
  const statusDiv = document.getElementById("status");
  const audioVisualizer = document.getElementById("audio-visualizer");
  const responseAudio = document.getElementById("response-audio");
  const sessionInfo = document.getElementById("session-info");

  // State management
  let mediaRecorder;
  let recordedChunks = [];
  let sessionId = null;
  let isRecording = false;
  let isProcessing = false;

  // Initialize session
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

  // Update UI state
  function updateUIState(state, message = "", icon = "") {
    const states = {
      ready: {
        class: "ready",
        buttonClass: "",
        icon: "fas fa-microphone",
        message: "Ready to listen",
      },
      listening: {
        class: "listening",
        buttonClass: "recording",
        icon: "fas fa-stop",
        message: "Listening... (click to stop)",
      },
      processing: {
        class: "processing",
        buttonClass: "processing",
        icon: "fas fa-spinner fa-spin",
        message: "Processing your request...",
      },
      responding: {
        class: "processing",
        buttonClass: "processing",
        icon: "fas fa-volume-up",
        message: "AI is responding...",
      },
      error: {
        class: "error",
        buttonClass: "",
        icon: "fas fa-exclamation-triangle",
        message: message || "Something went wrong",
      },
    };

    const currentState = states[state];
    if (!currentState) return;

    // Update status
    statusDiv.className = `status ${currentState.class}`;
    statusDiv.innerHTML = `<i class="${currentState.icon}"></i> ${currentState.message}`;

    // Update button
    voiceButton.className = `voice-button ${currentState.buttonClass}`;
    buttonIcon.className = currentState.icon;

    // Show/hide visualizer
    if (state === "listening") {
      audioVisualizer.classList.add("active");
    } else {
      audioVisualizer.classList.remove("active");
    }
  }

  // Handle voice interaction
  async function handleVoiceInteraction() {
    if (isProcessing) return;

    if (!isRecording) {
      startRecording();
    } else {
      stopRecording();
    }
  }

  // Start recording
  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100,
        },
      });

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
          updateUIState("error", "Recording too short. Please try again.");
          resetToReady();
          return;
        }
        processAudio(blob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorder.onerror = (error) => {
        console.error("MediaRecorder error:", error);
        updateUIState("error", "Recording failed. Please try again.");
        resetToReady();
      };

      mediaRecorder.start();
      isRecording = true;
      updateUIState("listening");
    } catch (error) {
      console.error("Microphone access error:", error);
      let errorMessage = "Could not access microphone. ";

      if (error.name === "NotAllowedError") {
        errorMessage += "Please allow microphone access and refresh the page.";
      } else if (error.name === "NotFoundError") {
        errorMessage += "No microphone found.";
      } else {
        errorMessage += "Please check your microphone settings.";
      }

      updateUIState("error", errorMessage);
      setTimeout(resetToReady, 3000);
    }
  }

  // Stop recording
  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      isRecording = false;
      isProcessing = true;
      updateUIState("processing");
    }
  }

  // Process audio with AI
  async function processAudio(audioBlob) {
    const formData = new FormData();
    formData.append("audio", audioBlob, `recording-${Date.now()}.webm`);

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000);

      const response = await fetch(`/agent/chat/${sessionId}`, {
        method: "POST",
        body: formData,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Server error (${response.status})`);
      }

      const result = await response.json();

      if (result.error) {
        updateUIState("error", result.message);
        if (result.audio_url) {
          responseAudio.src = result.audio_url;
          responseAudio.play().catch(() => {});
        }
        setTimeout(resetToReady, 3000);
      } else if (result.audio_url) {
        updateUIState("responding");
        responseAudio.src = result.audio_url;
        responseAudio.play().catch((error) => {
          console.warn("Audio playback failed:", error);
          updateUIState(
            "error",
            "Generated response but audio playback failed."
          );
          setTimeout(resetToReady, 3000);
        });
      } else {
        updateUIState("error", "Unexpected response from server.");
        setTimeout(resetToReady, 3000);
      }
    } catch (error) {
      console.error("Processing error:", error);

      if (error.name === "AbortError") {
        updateUIState("error", "Request timed out. Please try again.");
      } else if (!navigator.onLine) {
        updateUIState(
          "error",
          "You appear to be offline. Please check your connection."
        );
      } else {
        updateUIState("error", "Connection failed. Please try again.");
      }

      setTimeout(resetToReady, 3000);
    }
  }

  // Reset to ready state
  function resetToReady() {
    isRecording = false;
    isProcessing = false;
    updateUIState("ready");
  }

  // Event listeners
  voiceButton.addEventListener("click", handleVoiceInteraction);

  // Auto-continue conversation after AI response
  responseAudio.addEventListener("ended", () => {
    setTimeout(() => {
      if (!isProcessing) {
        updateUIState("ready");
        // Auto-start next recording after a brief pause
        setTimeout(() => {
          if (!isRecording && !isProcessing) {
            handleVoiceInteraction();
          }
        }, 1500);
      }
    }, 1000);
  });

  // Connection status monitoring
  window.addEventListener("online", () => {
    if (!isRecording && !isProcessing) {
      updateUIState("ready");
    }
  });

  window.addEventListener("offline", () => {
    updateUIState("error", "You are offline. Please check your connection.");
  });

  // Initialize
  initializeSession();
  updateUIState("ready");
});
