document.addEventListener("DOMContentLoaded", () => {
  // UI Elements
  const voiceButton = document.getElementById("voice-button");
  const buttonIcon = document.getElementById("button-icon");
  const statusDiv = document.getElementById("status");
  const responseAudio = document.getElementById("response-audio");

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
  function updateUIState(state, message = "") {
    voiceButton.disabled = false;
    voiceButton.classList.remove("recording", "processing");
    buttonIcon.classList.remove(
      "fa-microphone",
      "fa-stop",
      "fa-spinner",
      "fa-spin",
      "fa-volume-up",
      "fa-exclamation-triangle"
    );

    if (state === "ready") {
      buttonIcon.classList.add("fa-microphone");
      statusDiv.textContent = message || "Click to speak";
      statusDiv.classList.remove("error");
    } else if (state === "listening") {
      voiceButton.classList.add("recording");
      buttonIcon.classList.add("fa-stop");
      statusDiv.textContent = message || "Listening... Click to stop";
      statusDiv.classList.remove("error");
    } else if (state === "processing") {
      isProcessing = true;
      voiceButton.disabled = true;
      voiceButton.classList.add("processing");
      buttonIcon.classList.add("fa-spinner", "fa-spin");
      statusDiv.textContent = message || "Thinking...";
      statusDiv.classList.remove("error");
    } else if (state === "responding") {
      isProcessing = true;
      voiceButton.disabled = true;
      buttonIcon.classList.add("fa-volume-up");
      statusDiv.textContent = message || "AI is responding...";
      statusDiv.classList.remove("error");
    } else if (state === "error") {
      isProcessing = false;
      buttonIcon.classList.add("fa-exclamation-triangle");
      statusDiv.textContent = message || "Something went wrong";
      statusDiv.classList.add("error");
    }
  }

  // Handle voice interaction
  async function handleVoiceInteraction() {
    if (isProcessing) return; // Don't do anything if processing

    if (!isRecording) {
      // Start recording
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
        });
        mediaRecorder = new MediaRecorder(stream);
        recordedChunks = [];

        mediaRecorder.ondataavailable = (event) => {
          if (event.data.size > 0) recordedChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
          const audioBlob = new Blob(recordedChunks, { type: "audio/webm" });
          processAudio(audioBlob);
          stream.getTracks().forEach((track) => track.stop());
        };

        mediaRecorder.start();
        isRecording = true;
        updateUIState("listening");
      } catch (error) {
        console.error("Microphone access error:", error);
        updateUIState("error", "Could not access microphone.");
      }
    } else {
      // Stop recording
      mediaRecorder.stop();
      isRecording = false;
      updateUIState("processing");
    }
  }

  // Process audio with AI
  async function processAudio(audioBlob) {
    if (!sessionId) initializeSession();

    const formData = new FormData();
    formData.append("audio", audioBlob, `recording-${Date.now()}.webm`);

    try {
      const response = await fetch(`/agent/chat/${sessionId}`, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (result.error) {
        // Handle errors returned from the server (e.g., fallback audio)
        updateUIState("responding", result.message);
        if (result.audio_url) {
          responseAudio.src = result.audio_url;
          // Playback will trigger 'ended' event
        } else {
          // If even fallback audio failed, just reset
          setTimeout(() => updateUIState("ready"), 3000);
        }
      } else if (result.audio_url) {
        // Successful response
        updateUIState("responding");
        responseAudio.src = result.audio_url;
        // Playback will trigger 'ended' event
      }
    } catch (error) {
      console.error("Processing error:", error);
      updateUIState("error", "Connection failed. Please try again.");
      setTimeout(() => updateUIState("ready"), 3000);
    }
  }

  // Event listeners
  voiceButton.addEventListener("click", handleVoiceInteraction);

  // Auto-continue conversation after AI response
  responseAudio.addEventListener("ended", () => {
    isProcessing = false; // Processing is done
    updateUIState("ready", "Ready for your next message...");

    // This makes the conversation feel continuous
    setTimeout(() => {
      if (!isRecording && !isProcessing) {
        // Check state again
        handleVoiceInteraction(); // Auto-start next recording
      }
    }, 1000); // 1-second pause
  });

  responseAudio.addEventListener("error", () => {
    isProcessing = false;
    updateUIState("error", "Could not play audio response.");
    setTimeout(() => updateUIState("ready"), 3000);
  });

  // Initialize
  initializeSession();
  updateUIState("ready");
});
