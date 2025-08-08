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
        throw new Error("Failed to generate audio.");
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

  // === ECHO BOT V2 FUNCTIONALITY ===
  const startRecordingBtn = document.getElementById("start-recording");
  const stopRecordingBtn = document.getElementById("stop-recording");
  const recordingStatus = document.getElementById("recording-status");
  const echoPlayback = document.getElementById("echo-playback");
  const echoStatus = document.getElementById("echo-status");

  let mediaRecorder;
  let recordedChunks = [];

  // --- NEW: Function to handle the full Echo Bot v2 flow ---
  async function getEcho(audioBlob) {
    echoStatus.textContent = "Transcribing your voice...";
    const formData = new FormData();
    formData.append("audio", audioBlob, `recording-${Date.now()}.webm`);

    try {
      const response = await fetch("/tts/echo", {
        // Call the new endpoint
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to process audio.");
      }

      echoStatus.textContent = "Generating my response...";
      const result = await response.json();

      echoPlayback.src = result.audio_url;
      echoPlayback.play();
      echoStatus.textContent = "Done!";
    } catch (error) {
      console.error("Echo Error:", error);
      echoStatus.textContent = `Error: ${error.message}`;
    }
  }

  startRecordingBtn.addEventListener("click", async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      recordedChunks = [];
      echoStatus.textContent = ""; // Clear previous status
      echoPlayback.src = ""; // Clear previous audio

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunks.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const blob = new Blob(recordedChunks, { type: "audio/webm" });
        // Don't play the user's audio back, instead, send it for processing
        // const audioUrl = URL.createObjectURL(blob);
        // echoPlayback.src = audioUrl;

        getEcho(blob); // Call the new handler function

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
