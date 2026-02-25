document.getElementById('audioFile').addEventListener('change', function(e) {
    const fileName = e.target.files[0] ? e.target.files[0].name : 'Choose Audio File';
    document.getElementById('fileName').textContent = fileName;
});

document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const fileInput = document.getElementById('audioFile');
    const file = fileInput.files[0];
    
    if (!file) {
        alert("Please select a file first.");
        return;
    }

    uploadAndPredict(file);
});

// Recording Logic
const recordBtn = document.getElementById('recordBtn');
let mediaRecorder;
let audioChunks = [];

recordBtn.addEventListener('click', async () => {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert("Microphone access is not supported in this browser.");
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const audioFile = new File([audioBlob], "recording.wav", { type: "audio/wav" });
            
            // Update UI to show we have a file
            document.getElementById('fileName').textContent = "Recorded Audio";
            
            // Send to backend
            uploadAndPredict(audioFile);
        };

        // Start Recording
        mediaRecorder.start();
        recordBtn.textContent = "Recording...";
        recordBtn.classList.add("recording");
        recordBtn.disabled = true;

        // Stop after 3 seconds
        setTimeout(() => {
            mediaRecorder.stop();
            recordBtn.textContent = "🎤 Record (3s)";
            recordBtn.classList.remove("recording");
            recordBtn.disabled = false;
            
            // Stop all tracks to release microphone
            stream.getTracks().forEach(track => track.stop());
        }, 3100); 

    } catch (err) {
        console.error("Error accessing microphone:", err);
        alert("Could not access microphone. Please ensure you have granted permission.");
    }
});

// Live Detection Logic
const liveBtn = document.getElementById('liveBtn');
const liveStatus = document.getElementById('liveStatus');
const liveResult = document.getElementById('liveResult');
let isLive = false;
let liveStream = null;
let liveRecorder = null;
let liveInterval = null;

liveBtn.addEventListener('click', async () => {
    if (!isLive) {
        // Start Live Mode
        startLiveDetection();
    } else {
        // Stop Live Mode
        stopLiveDetection();
    }
});

async function startLiveDetection() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert("Microphone access is not supported.");
        return;
    }

    try {
        liveStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        isLive = true;
        liveBtn.textContent = "⏹ Stop Live Detection";
        liveBtn.classList.add("active");
        liveStatus.classList.remove("hidden");
        document.getElementById('result').classList.add('hidden'); // Hide static result

        runLiveLoop();

    } catch (err) {
        console.error("Error starting live detection:", err);
        alert("Could not access microphone.");
    }
}

function stopLiveDetection() {
    isLive = false;
    liveBtn.textContent = "🔴 Start Live Detection";
    liveBtn.classList.remove("active");
    liveStatus.classList.add("hidden");
    liveResult.textContent = "";
    liveResult.className = "live-result";

    if (liveStream) {
        liveStream.getTracks().forEach(track => track.stop());
        liveStream = null;
    }
    if (liveRecorder && liveRecorder.state !== 'inactive') {
        liveRecorder.stop();
    }
    clearTimeout(liveInterval);
}

function runLiveLoop() {
    if (!isLive) return;

    // Create a new recorder for this segment
    liveRecorder = new MediaRecorder(liveStream);
    let chunks = [];

    liveRecorder.ondataavailable = e => chunks.push(e.data);
    
    liveRecorder.onstop = async () => {
        if (!isLive) return; // Stopped while recording
        
        const blob = new Blob(chunks, { type: 'audio/wav' });
        const file = new File([blob], "live_segment.wav", { type: "audio/wav" });
        
        // Send to backend without blocking UI
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const response = await fetch('/predict', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            if (response.ok) {
                updateLiveUI(data);
            }
        } catch (e) {
            console.error("Live prediction error:", e);
        }
        
        // Immediately start next loop if still live
        if (isLive) {
            runLiveLoop();
        }
    };

    liveRecorder.start();
    
    // Record for 3 seconds (model's expected duration)
    // We use setTimeout to stop it.
    setTimeout(() => {
        if (liveRecorder && liveRecorder.state === 'recording') {
            liveRecorder.stop();
        }
    }, 3000); 
}

function updateLiveUI(data) {
    if (data.prediction === "Drone Detected") {
        liveResult.textContent = `⚠️ DRONE DETECTED (${data.confidence})`;
        liveResult.className = "live-result drone-alert";
        // Optional: Play a beep sound?
    } else {
        liveResult.textContent = `✅ No Drone Detected (${data.confidence})`;
        liveResult.className = "live-result safe-status";
    }
}

async function uploadAndPredict(file) {
    // UI Reset
    document.getElementById('result').classList.add('hidden');
    document.getElementById('loading').classList.remove('hidden');
    
    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/predict', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Something went wrong');
        }

        displayResult(data);

    } catch (error) {
        alert(error.message);
    } finally {
        document.getElementById('loading').classList.add('hidden');
    }
}

function displayResult(data) {
    const resultDiv = document.getElementById('result');
    const iconDiv = document.getElementById('statusIcon');
    const textDiv = document.getElementById('predictionText');
    const barDiv = document.getElementById('confidenceBar');
    const valSpan = document.getElementById('confidenceValue');
    const rawSpan = document.getElementById('rawScore');

    resultDiv.classList.remove('hidden');
    
    // Update values
    valSpan.textContent = data.confidence;
    rawSpan.textContent = data.raw_score.toFixed(4);
    
    const confidencePercent = parseFloat(data.confidence) * 100;
    barDiv.style.width = `${confidencePercent}%`;

    if (data.prediction === "Drone Detected") {
        iconDiv.textContent = "🚨";
        textDiv.textContent = "Drone Detected!";
        textDiv.style.color = "#e74c3c"; // Red
        barDiv.style.backgroundColor = "#e74c3c";
    } else {
        iconDiv.textContent = "✅";
        textDiv.textContent = "No Drone Detected";
        textDiv.style.color = "#2ecc71"; // Green
        barDiv.style.backgroundColor = "#2ecc71";
    }
}
