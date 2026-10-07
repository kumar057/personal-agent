// State
let voiceOutputEnabled = false;
let isListening = false;
let recognition = null;

// DOM Elements
const messagesContainer = document.getElementById("messages-container");
const userInput = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");
const micBtn = document.getElementById("mic-btn");
const voiceToggleBtn = document.getElementById("voice-toggle-btn");
const modelSelect = document.getElementById("model-select");
const activityIndicator = document.getElementById("activity-indicator");
const activityText = document.getElementById("activity-text");

// Initialize Speech Recognition
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";

    recognition.onresult = (event) => {
        let transcript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
            transcript += event.results[i][0].transcript;
        }
        userInput.value = transcript;
    };

    recognition.onend = () => {
        isListening = false;
        micBtn.classList.remove("listening");
        if (userInput.value.trim().length > 0) {
            sendMessage();
        }
    };

    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        isListening = false;
        micBtn.classList.remove("listening");
    };
} else {
    micBtn.title = "Speech recognition not supported in this browser";
}

// Navigation Tabs
document.querySelectorAll(".nav-item").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".nav-item").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
        
        btn.classList.add("active");
        const tabId = btn.getAttribute("data-tab");
        document.getElementById(`tab-${tabId}`).classList.add("active");
        
        const titles = {
            chat: "Personal Assistant",
            productivity: "Tasks & Notes",
            knowledge: "Personal Knowledge Base",
            models: "Local Models Manager"
        };
        document.getElementById("page-title").innerText = titles[tabId] || "Assistant";
        
        if (tabId === "productivity") loadProductivity();
        if (tabId === "models") loadModels();
    });
});

// Voice Toggle Button
voiceToggleBtn.addEventListener("click", () => {
    voiceOutputEnabled = !voiceOutputEnabled;
    voiceToggleBtn.classList.toggle("active", voiceOutputEnabled);
    voiceToggleBtn.innerHTML = voiceOutputEnabled 
        ? '<i class="fa-solid fa-volume-high"></i>' 
        : '<i class="fa-solid fa-volume-xmark"></i>';
});

// Microphone Toggle
micBtn.addEventListener("click", () => {
    if (!recognition) {
        alert("Speech recognition is supported natively in Google Chrome, Microsoft Edge, and Brave.");
        return;
    }
    if (isListening) {
        recognition.stop();
        isListening = false;
        micBtn.classList.remove("listening");
    } else {
        userInput.value = "";
        recognition.start();
        isListening = true;
        micBtn.classList.add("listening");
    }
});

// Send Message on Enter
userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
sendBtn.addEventListener("click", () => sendMessage());

function quickSend(prompt) {
    userInput.value = prompt;
    sendMessage();
}

// Append Message Bubble
function appendMessage(role, text) {
    const bubble = document.createElement("div");
    bubble.className = `message-bubble ${role}`;
    
    const avatar = document.createElement("div");
    avatar.className = "bubble-avatar";
    avatar.innerHTML = role === "user" ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';

    const content = document.createElement("div");
    content.className = "bubble-content";
    
    // Simple markdown formatting
    content.innerHTML = formatMarkdown(text);

    bubble.appendChild(avatar);
    bubble.appendChild(content);
    messagesContainer.appendChild(bubble);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    return content;
}

function formatMarkdown(text) {
    if (!text) return "";
    let formatted = text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.*?)\*/g, "<em>$1</em>")
        .replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>")
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\n\n/g, "</p><p>")
        .replace(/\n/g, "<br>");
    return `<p>${formatted}</p>`;
}

// Send Chat Message via SSE Streaming
async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    appendMessage("user", text);
    userInput.value = "";

    activityIndicator.classList.remove("hidden");
    activityText.innerText = "Agent is reasoning...";

    const currentModel = modelSelect.value;

    try {
        const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                model: currentModel,
                voice_output: voiceOutputEnabled
            })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantBubble = null;
        let assistantContentEl = null;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split("\n\n");

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    try {
                        const event = JSON.parse(line.replace("data: ", ""));
                        if (event.type === "thought") {
                            activityText.innerText = event.content;
                        } else if (event.type === "tool_start") {
                            activityText.innerText = `⚡ Running tool: ${event.tool}...`;
                        } else if (event.type === "tool_result") {
                            activityText.innerText = `Observed result for ${event.tool}. Synthesizing...`;
                        } else if (event.type === "answer") {
                            activityIndicator.classList.add("hidden");
                            if (!assistantBubble) {
                                assistantContentEl = appendMessage("assistant", event.content);
                            } else {
                                assistantContentEl.innerHTML = formatMarkdown(event.content);
                            }
                        } else if (event.type === "done") {
                            activityIndicator.classList.add("hidden");
                        }
                    } catch (e) {}
                }
            }
        }
    } catch (err) {
        activityIndicator.classList.add("hidden");
        appendMessage("assistant", `⚠️ Connection error: ${err.message}`);
    }
}

// Telemetry Poller
async function updateTelemetry() {
    try {
        const res = await fetch("/api/status");
        const data = await res.parse ? await res.parse() : await res.json();
        
        // System metrics
        if (data.system) {
            const cpu = data.system.cpu_usage_percent || 0;
            const ramPct = data.system.ram_percent || 0;
            const ramUsed = data.system.ram_used_gb || 0;
            const ramTotal = data.system.ram_total_gb || 0;
            const battery = data.system.battery || {};

            document.getElementById("metric-cpu").innerText = `${cpu}%`;
            document.getElementById("bar-cpu").style.width = `${cpu}%`;

            document.getElementById("metric-ram").innerText = `${ramUsed} / ${ramTotal} GB`;
            document.getElementById("bar-ram").style.width = `${ramPct}%`;

            const plugged = battery.power_plugged ? '<i class="fa-solid fa-bolt" style="color: #fbbf24"></i> ' : '';
            document.getElementById("metric-battery").innerHTML = `${plugged}${battery.percent}%`;
        }

        // Provider & Engine status
        const pill = document.getElementById("ollama-pill");
        const statusText = document.getElementById("ollama-status-text");
        
        if (data.configured) {
            pill.className = "status-pill online";
            statusText.innerText = `${data.provider_name || data.provider}: Ready`;
            
            // Add active cloud model option if not already in dropdown
            if (data.current_model && !modelSelect.querySelector(`option[value='${data.current_model}']`)) {
                const opt = document.createElement("option");
                opt.value = data.current_model;
                opt.innerText = `${data.current_model} (${data.provider_name || 'Cloud'})`;
                opt.selected = true;
                modelSelect.prepend(opt);
            }
        } else if (data.ollama_online) {
            pill.className = "status-pill online";
            statusText.innerText = `Ollama: Online (${data.ollama_version || "v0.40"})`;
            
            if (data.models && data.models.length > 0) {
                const currentVal = modelSelect.value;
                modelSelect.innerHTML = "";
                data.models.forEach(m => {
                    const opt = document.createElement("option");
                    opt.value = m;
                    opt.innerText = m;
                    if (m === currentVal || m.startsWith("llama3.2")) opt.selected = true;
                    modelSelect.appendChild(opt);
                });
            }
        } else {
            pill.className = "status-pill offline";
            statusText.innerText = "AI: No Key / Offline";
        }
    } catch (e) {
        console.error("Telemetry fetch error:", e);
    }
}

async function saveApiKey() {
    const provider = document.getElementById("cloud-provider-select").value;
    const key = document.getElementById("cloud-api-key-input").value.trim();
    const statusEl = document.getElementById("key-save-status");
    
    if (!key) {
        statusEl.innerHTML = '<span style="color: var(--danger)">Please enter a valid API key.</span>';
        return;
    }
    
    statusEl.innerHTML = '<span style="color: var(--primary)"><i class="fa-solid fa-spinner fa-spin"></i> Saving key...</span>';
    try {
        const res = await fetch("/api/config/key", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ provider, key })
        });
        const data = await res.json();
        if (data.success) {
            statusEl.innerHTML = `<span style="color: var(--success)"><i class="fa-solid fa-check"></i> Connected! ${provider.toUpperCase()} is now your active AI engine.</span>`;
            document.getElementById("cloud-api-key-input").value = "";
            updateTelemetry();
        } else {
            statusEl.innerHTML = `<span style="color: var(--danger)">Failed to save key.</span>`;
        }
    } catch (err) {
        statusEl.innerHTML = `<span style="color: var(--danger)">Error: ${err.message}</span>`;
    }
}

setInterval(updateTelemetry, 4000);
updateTelemetry();

// Productivity Manager
async function loadProductivity() {
    // Load Todos
    const todosRes = await fetch("/api/todos?status=pending");
    const todos = await todosRes.json();
    const todoListEl = document.getElementById("todo-list");
    todoListEl.innerHTML = "";
    if (todos.length === 0) {
        todoListEl.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">No pending tasks. Great job!</p>';
    } else {
        todos.forEach(t => {
            const div = document.createElement("div");
            div.className = "item-card";
            div.innerHTML = `
                <div>
                    <strong>${t.task}</strong>
                    <div style="font-size: 11px; color: var(--text-muted);">Priority: ${t.priority}</div>
                </div>
                <button class="btn-outline btn-sm" onclick="completeTodoItem(${t.id})"><i class="fa-solid fa-check"></i></button>
            `;
            todoListEl.appendChild(div);
        });
    }

    // Load Notes
    const notesRes = await fetch("/api/notes");
    const notes = await notesRes.json();
    const notesListEl = document.getElementById("notes-list");
    notesListEl.innerHTML = "";
    if (notes.length === 0) {
        notesListEl.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">No saved notes yet.</p>';
    } else {
        notes.forEach(n => {
            const div = document.createElement("div");
            div.className = "item-card";
            div.innerHTML = `
                <div>
                    <strong>${n.title}</strong>
                    <p style="font-size: 12px; color: var(--text-muted);">${n.content.substring(0, 80)}...</p>
                </div>
            `;
            notesListEl.appendChild(div);
        });
    }
}

async function handleAddTodo() {
    const input = document.getElementById("new-todo-input");
    const priority = document.getElementById("todo-priority-select").value;
    if (!input.value.trim()) return;

    await fetch("/api/todos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: input.value.trim(), priority })
    });
    input.value = "";
    loadProductivity();
}

async function completeTodoItem(id) {
    await fetch(`/api/todos/${id}/complete`, { method: "POST" });
    loadProductivity();
}

async function handleAddNote() {
    const titleInput = document.getElementById("new-note-title");
    const contentInput = document.getElementById("new-note-content");
    if (!titleInput.value.trim() || !contentInput.value.trim()) return;

    await fetch("/api/notes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: titleInput.value.trim(), content: contentInput.value.trim() })
    });
    titleInput.value = "";
    contentInput.value = "";
    loadProductivity();
}

// File Upload for Knowledge Base
const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-upload");
const uploadStatus = document.getElementById("upload-status");

fileInput.addEventListener("change", async (e) => {
    if (e.target.files.length > 0) {
        const file = e.target.files[0];
        const formData = new FormData();
        formData.append("file", file);

        uploadStatus.innerHTML = `<p style="color: var(--primary)"><i class="fa-solid fa-spinner fa-spin"></i> Indexing ${file.name} into Knowledge Base...</p>`;

        try {
            const res = await fetch("/api/knowledge/upload", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (data.success) {
                uploadStatus.innerHTML = `<p style="color: var(--success)"><i class="fa-solid fa-check-circle"></i> Successfully indexed "${file.name}" (${data.characters} characters).</p>`;
            } else {
                uploadStatus.innerHTML = `<p style="color: var(--danger)">Upload error: ${data.error || "Unknown"}</p>`;
            }
        } catch (err) {
            uploadStatus.innerHTML = `<p style="color: var(--danger)">Upload error: ${err.message}</p>`;
        }
    }
});

// Model Manager
async function loadModels() {
    const res = await fetch("/api/models");
    const data = await res.json();
    const listEl = document.getElementById("installed-models-list");
    listEl.innerHTML = "";
    
    if (!data.installed || data.installed.length === 0) {
        listEl.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">No models installed locally yet. Download one below!</p>';
    } else {
        data.installed.forEach(m => {
            const div = document.createElement("div");
            div.className = "model-card";
            div.innerHTML = `
                <div class="model-badge speed">Installed</div>
                <h4>${m.name}</h4>
                <p>Size: ${(m.size / (1024**3)).toFixed(2)} GB</p>
            `;
            listEl.appendChild(div);
        });
    }
}

async function triggerPullModel(modelName) {
    const progressBox = document.getElementById("pull-progress-box");
    const statusText = document.getElementById("pull-status-text");
    const progressBar = document.getElementById("pull-progress-bar");

    progressBox.classList.remove("hidden");
    statusText.innerText = `Starting download for ${modelName}...`;

    try {
        const response = await fetch("/api/models/pull", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ model_name: modelName })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split("\n\n");
            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    try {
                        const event = JSON.parse(line.replace("data: ", ""));
                        if (event.status) {
                            statusText.innerText = `${event.status} ${event.completed ? "(Complete!)" : ""}`;
                            if (event.total && event.completed) {
                                const pct = Math.round((event.completed / event.total) * 100);
                                progressBar.style.width = `${pct}%`;
                            }
                        }
                    } catch (e) {}
                }
            }
        }
        statusText.innerText = `✅ Model ${modelName} installed successfully!`;
        updateTelemetry();
        loadModels();
    } catch (err) {
        statusText.innerText = `Download error: ${err.message}`;
    }
}
