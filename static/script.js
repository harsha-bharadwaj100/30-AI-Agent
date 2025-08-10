document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const startRecordingBtn = document.getElementById("start-recording");
  const stopRecordingBtn = document.getElementById("stop-recording");
  const playbackAudio = document.getElementById("echo-playback"); // Use existing audio element for playback
  const statusDiv = document.getElementById("echo-status");

  let mediaRecorder;
  let recordedChunks = [];

  startRecordingBtn.addEventListener("click", async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorder = new MediaRecorder(stream);
      recordedChunks = [];
      statusDiv.textContent = "";
      playbackAudio.src = "";

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) recordedChunks.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const blob = new Blob(recordedChunks, { type: "audio/webm" });
        statusDiv.textContent = "Processing your request...";

        // Prepare FormData and send to /llm/query
        const formData = new FormData();
        formData.append("audio", blob, `recording-${Date.now()}.webm`);

        try {
          const response = await fetch("/llm/query", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || "Request failed");
          }

          const data = await response.json();
          playbackAudio.src = data.audio_url;
          playbackAudio.play();
          statusDiv.textContent = "Here is my response!";
        } catch (error) {
          console.error("Error:", error);
          statusDiv.textContent = "Error: " + error.message;
        }
      };

      mediaRecorder.start();
      startRecordingBtn.disabled = true;
      stopRecordingBtn.disabled = false;
      statusDiv.textContent = "Recording...";
    } catch (err) {
      console.error("Microphone access error:", err);
      alert(
        "Could not access microphone. Please allow microphone permissions."
      );
    }
  });

  stopRecordingBtn.addEventListener("click", () => {
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
      startRecordingBtn.disabled = false;
      stopRecordingBtn.disabled = true;
      statusDiv.textContent = "";
    }
  });
});
