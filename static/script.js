document.addEventListener("DOMContentLoaded", () => {
  // === TEXT TO SPEECH FUNCTIONALITY ===
  // (Code from previous day, no changes needed)
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

  // === ECHO & TRANSCRIBE BOT FUNCTIONALITY ===
  const startRecordingBtn = document.getElementById("start-recording");
  const stopRecordingBtn = document.getElementById("stop-recording");
  const recordingStatus = document.getElementById("recording-status");
  const echoPlayback = document.getElementById("echo-playback");
  const transcriptionStatus = document.getElementById("transcription-status");
  const transcriptionResult = document.getElementById("transcription-result");

  let mediaRecorder;
  let recordedChunks = [];

  // --- UPDATED: Function to transcribe audio ---
  async function transcribeAudio(audioBlob) {
    transcriptionStatus.textContent = "Transcribing...";
    transcriptionResult.style.display = "none";

    const formData = new FormData();
    formData.append("audio", audioBlob, `recording-${Date.now()}.webm`);

    try {
      const response = await fetch("/transcribe/file", {
        // Use the new endpoint
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Transcription failed.");
      }

      const result = await response.json();
      transcriptionStatus.textContent = "Transcription successful!";
      transcriptionResult.textContent = `"${result.transcription}"`;
      transcriptionResult.style.display = "block";
    } catch (error) {
      console.error("Transcription Error:", error);
      transcriptionStatus.textContent = `Transcription failed: ${error.message}`;
    }
  }

  startRecordingBtn.addEventListener("click", async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      recordedChunks = [];
      transcriptionStatus.textContent = ""; // Clear previous status
      transcriptionResult.style.display = "none";

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(recordedChunks, { type: "audio/webm" });
        const audioUrl = URL.createObjectURL(blob);
        echoPlayback.src = audioUrl;

        // --- Call the new transcribe function ---
        transcribeAudio(blob);

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
        "Could not access microphone. Please ensure permission is granted."
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
