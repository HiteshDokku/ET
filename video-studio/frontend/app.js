document.addEventListener('DOMContentLoaded', () => {
    const articleInput = document.getElementById('article-input');
    const generateBtn = document.getElementById('generate-btn');
    const loader = document.getElementById('loader');
    const errorMessage = document.getElementById('error-message');
    const videoOutput = document.getElementById('video-output');
    const resultVideo = document.getElementById('result-video');

    generateBtn.addEventListener('click', async () => {
        const article = articleInput.value.trim();
        
        if (!article) {
            showError("Please enter a business news article.");
            return;
        }

        // Reset UI states
        hideError();
        videoOutput.classList.add('hidden');
        loader.classList.remove('hidden');
        generateBtn.disabled = true;

        try {
            // Adjust the port if necessary based on where FastAPI runs
            const response = await fetch("http://127.0.0.1:8000/generate-video", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ article })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Failed to generate video.");
            }

            // Setup video
            resultVideo.src = `http://127.0.0.1:8000/${data.video_url}`;
            videoOutput.classList.remove('hidden');
            resultVideo.play();
            
        } catch (error) {
            console.error("Error:", error);
            showError(error.message);
        } finally {
            loader.classList.add('hidden');
            generateBtn.disabled = false;
        }
    });

    function showError(message) {
        errorMessage.textContent = message;
        errorMessage.classList.remove('hidden');
    }

    function hideError() {
        errorMessage.classList.add('hidden');
    }
});
