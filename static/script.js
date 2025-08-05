document.addEventListener("DOMContentLoaded", () => {
  // === TEXT TO SPEECH FUNCTIONALITY ===
  const ttsForm = document.getElementById("tts-form");
  const textInput = document.getElementById("text-input");
  const audioPlayback = document.getElementById("audio-playback");
  const submitButton = document.getElementById("submit-button");

  // TTS form submission handler
  ttsForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const text = textInput.value;
    if (!text) {
      alert("Please enter some text.");
      return;
    }

    submitButton.disabled = true;
    submitButton.textContent = "Generating...";

    try {
      const response = await fetch("/generate-audio/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: text }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate audio.");
      }

      const data = await response.json();
      const audioUrl = data.audio_url;

      audioPlayback.src = audioUrl;
      audioPlayback.play();
    } catch (error) {
      console.error("Error:", error);
      alert("An error occurred: " + error.message);
    } finally {
      submitButton.disabled = false;
      submitButton.textContent = "Generate Audio";
    }
  });

  // === ECHO BOT FUNCTIONALITY ===
  const startRecordingBtn = document.getElementById("start-recording");
  const stopRecordingBtn = document.getElementById("stop-recording");
  const recordingStatus = document.getElementById("recording-status");
  const echoPlayback = document.getElementById("echo-playback");

  let mediaRecorder;
  let recordedChunks = [];

  // Start recording handler
  startRecordingBtn.addEventListener("click", async () => {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      // Create MediaRecorder instance
      mediaRecorder = new MediaRecorder(stream);
      recordedChunks = [];

      // Set up event handlers
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        // Create blob from recorded chunks
        const blob = new Blob(recordedChunks, {
          type: "audio/webm",
        });

        // Create URL for the blob and set it as audio source
        const audioUrl = URL.createObjectURL(blob);
        echoPlayback.src = audioUrl;

        // Show the audio player
        echoPlayback.style.display = "block";

        // Stop all tracks to release microphone
        stream.getTracks().forEach((track) => track.stop());

        // Hide recording status
        recordingStatus.classList.remove("active");
      };

      // Start recording
      mediaRecorder.start();

      // Update UI
      startRecordingBtn.disabled = true;
      stopRecordingBtn.disabled = false;
      recordingStatus.classList.add("active");
    } catch (error) {
      console.error("Error accessing microphone:", error);
      alert(
        "Could not access microphone. Please ensure you have granted permission."
      );
    }
  });

  // Stop recording handler
  stopRecordingBtn.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();

      // Update UI
      startRecordingBtn.disabled = false;
      stopRecordingBtn.disabled = true;
    }
  });
});
