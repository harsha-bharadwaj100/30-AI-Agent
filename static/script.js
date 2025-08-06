document.addEventListener("DOMContentLoaded", () => {
  // === TEXT TO SPEECH FUNCTIONALITY ===
  const ttsForm = document.getElementById("tts-form");
  const textInput = document.getElementById("text-input");
  const audioPlayback = document.getElementById("audio-playback");
  const submitButton = document.getElementById("submit-button");

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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate audio.");
      }
      const data = await response.json();
      audioPlayback.src = data.audio_url;
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
  const uploadStatus = document.getElementById("upload-status"); // New element

  let mediaRecorder;
  let recordedChunks = [];

  // --- NEW: Function to upload audio ---
  async function uploadAudio(audioBlob) {
    uploadStatus.textContent = "Uploading...";
    const formData = new FormData();
    // The filename can be customized. Using a timestamp for uniqueness.
    formData.append("audio", audioBlob, `recording-${Date.now()}.webm`);

    try {
      const response = await fetch("/upload-audio/", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Upload failed. Server responded with an error.");
      }
      const result = await response.json();
      uploadStatus.textContent = `Upload successful: ${
        result.filename
      } (${Math.round(result.size_in_bytes / 1024)} KB)`;
    } catch (error) {
      console.error("Upload Error:", error);
      uploadStatus.textContent = `Upload failed: ${error.message}`;
    }
  }

  startRecordingBtn.addEventListener("click", async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      recordedChunks = [];
      uploadStatus.textContent = ""; // Clear previous status

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(recordedChunks, { type: "audio/webm" });
        const audioUrl = URL.createObjectURL(blob);
        echoPlayback.src = audioUrl;
        echoPlayback.style.display = "block";

        // --- NEW: Call the upload function ---
        uploadAudio(blob);

        stream.getTracks().forEach((track) => track.stop());
        recordingStatus.classList.remove("active");
      };

      mediaRecorder.start();
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

  stopRecordingBtn.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      startRecordingBtn.disabled = false;
      stopRecordingBtn.disabled = true;
    }
  });
});
