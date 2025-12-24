class ChatBot {
    constructor() {
        this.config = {
            apiKey: "", // 🔴 REPLACE
            apiUrl: "https://api.cohere.ai/v2/chat",
            model: "command-a-03-2025",

            systemPrompt: `You are a helpful, professional, and friendly AI assistant for a company website.

Personality & Tone:
- Warm, professional, approachable
- Concise, clear, and helpful
- Friendly but respectful
- Enthusiastic about helping users

Capabilities:
- Answer questions about solar products & services
- Guide users on solar panel selection
- Provide basic technical explanations
- Escalate complex issues politely

Rules:
- Never ask for sensitive data
- Ask clarifying questions when needed
- Suggest human support if required

Response Style:
- Bullet points where useful
- Light emojis 😊 (not excessive)
- Actionable suggestions

Special Instruction:
When a user asks about solar panels for a city (e.g., Mumbai), respond in the structured Sunrise Power format and include social links at the end.`,

            welcomeMessage: {
                title: "👋 Welcome!",
                message: "Hi! I'm your solar assistant. How can I help you today?",
                autoSend: true
            }
        };

        this.isOpen = false;
        this.isProcessing = false;
        this.conversationHistory = [];

        this.initElements();
        this.initEvents();
        this.initWelcome();
    }

    /* ---------------- UI INIT ---------------- */

    initElements() {
        this.chatButton = document.getElementById("chatButton");
        this.chatOverlay = document.getElementById("chatOverlay");
        this.chatModal = document.getElementById("chatModal");
        this.closeBtn = document.getElementById("closeBtn");
        this.chatMessages = document.getElementById("chatMessages");
        this.messageInput = document.getElementById("messageInput");
        this.sendBtn = document.getElementById("sendBtn");
        this.typingIndicator = document.getElementById("typingIndicator");
    }

    initEvents() {
        this.chatButton.onclick = () => this.toggleChat();
        this.closeBtn.onclick = () => this.closeChat();
        this.chatOverlay.onclick = () => this.closeChat();
        this.sendBtn.onclick = () => this.sendMessage();

        this.messageInput.addEventListener("keydown", e => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
    }

    initWelcome() {
        if (this.config.welcomeMessage.autoSend) {
            setTimeout(() => {
                this.addMessage(this.config.welcomeMessage.message, "bot");
            }, 600);
        }
    }

    /* ---------------- CHAT FLOW ---------------- */

    toggleChat() {
        this.isOpen ? this.closeChat() : this.openChat();
    }

    openChat() {
        this.isOpen = true;
        this.chatModal.style.display = "flex";
    }

    closeChat() {
        this.isOpen = false;
        this.chatModal.style.display = "none";
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isProcessing) return;

        this.addMessage(message, "user");
        this.messageInput.value = "";
        this.setProcessing(true);
        this.showTyping(true);

        try {
            const reply = await this.callCohere(message);
            this.addMessage(reply, "bot");
        } catch (err) {
            console.error(err);
            this.addMessage("⚠️ Sorry, something went wrong. Please try again.", "bot");
        } finally {
            this.setProcessing(false);
            this.showTyping(false);
        }
    }

    /* ---------------- COHERE API (FINAL FIX) ---------------- */

    async callCohere(userMessage) {
        const messages = [];

        // ✅ Inject system prompt ONCE as first user message
        if (this.conversationHistory.length === 0) {
            messages.push({
                role: "user",
                content: this.config.systemPrompt
            });
        }

        // Add conversation history
        this.conversationHistory.forEach(m => {
            messages.push({
                role: m.role,
                content: m.text
            });
        });

        // Add current user message
        messages.push({
            role: "user",
            content: userMessage
        });

        const response = await fetch(this.config.apiUrl, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${this.config.apiKey}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                model: this.config.model,
                messages: messages
            })
        });

        if (!response.ok) {
            const errText = await response.text();
            throw new Error(errText);
        }

        const data = await response.json();
        const botText = data.message.content[0].text;

        // Save history
        this.conversationHistory.push(
            { role: "user", text: userMessage },
            { role: "assistant", text: botText }
        );

        // Limit history size
        if (this.conversationHistory.length > 20) {
            this.conversationHistory.splice(0, 2);
        }

        return botText;
    }

    /* ---------------- UI HELPERS ---------------- */

    addMessage(text, sender) {
        const div = document.createElement("div");
        div.className = `message ${sender}`;
        div.textContent = text;
        this.chatMessages.appendChild(div);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    showTyping(show) {
        if (this.typingIndicator) {
            this.typingIndicator.style.display = show ? "block" : "none";
        }
    }

    setProcessing(state) {
        this.isProcessing = state;
        this.sendBtn.disabled = state;
        this.messageInput.disabled = state;
    }
}

/* ---------------- INIT ---------------- */

document.addEventListener("DOMContentLoaded", () => {
    window.chatbot = new ChatBot();
});
