document.addEventListener("DOMContentLoaded", () => {
  // Get references to the HTML elements
  const ttsForm = document.getElementById("tts-form");
  const textInput = document.getElementById("text-input");
  const audioPlayback = document.getElementById("audio-playback");
  const submitButton = document.getElementById("submit-button");

  // Listen for the form's submit event
  ttsForm.addEventListener("submit", async (event) => {
    // Prevent the default form submission which reloads the page
    event.preventDefault();

    const text = textInput.value;
    if (!text) {
      alert("Please enter some text.");
      return;
    }

    // Disable button to prevent multiple clicks
    submitButton.disabled = true;
    submitButton.textContent = "Generating...";

    try {
      // Send a POST request to our backend API
      const response = await fetch("/generate-audio/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: text }),
      });

      if (!response.ok) {
        // If the server responded with an error, show it
        const errorData = await response.json();
        throw new Error(errorData.detail || "Failed to generate audio.");
      }

      // Get the audio URL from the successful response
      const data = await response.json();
      const audioUrl = data.audio_url;

      // Set the audio source and play it
      audioPlayback.src = audioUrl;
      audioPlayback.play();
    } catch (error) {
      console.error("Error:", error);
      alert("An error occurred: " + error.message);
    } finally {
      // Re-enable the button
      submitButton.disabled = false;
      submitButton.textContent = "Generate Audio";
    }
  });
});
