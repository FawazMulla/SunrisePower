class ChatBot {
    constructor() {
        this.config = {
            apiKey: "", // Will be loaded from backend
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
        
        // CRM integration properties
        this.sessionId = this.generateSessionId();
        this.userInfo = {};
        this.conversationContext = {};

        this.initElements();
        this.initEvents();
        this.loadApiKey();
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

    async loadApiKey() {
        try {
            const response = await fetch('/api/integrations/config/cohere-key/');
            
            if (response.ok) {
                const data = await response.json();
                this.config.apiKey = data.api_key;
            } else {
                console.warn('Could not load Cohere API key from backend:', response.status, response.statusText);
                // Try to get error details
                try {
                    const errorData = await response.json();
                    console.warn('Error details:', errorData);
                } catch (e) {
                    console.warn('Could not parse error response');
                }
            }
        } catch (error) {
            console.warn('Error loading Cohere API key:', error);
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
        
        // Send conversation data to CRM when chat is closed (if there was meaningful interaction)
        this.sendConversationToCRM();
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isProcessing) return;

        // Ensure API key is loaded before sending message
        if (!this.config.apiKey) {
            await this.loadApiKey();
        }

        // Check if we still don't have an API key
        if (!this.config.apiKey) {
            this.addMessage("⚠️ Chatbot service is temporarily unavailable. Please try again later.", "bot");
            return;
        }

        this.addMessage(message, "user");
        this.messageInput.value = "";
        this.setProcessing(true);
        this.showTyping(true);

        // Extract user information from message
        this.extractUserInfo(message);

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

    /* ---------------- CRM INTEGRATION ---------------- */

    generateSessionId() {
        return 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    extractUserInfo(message) {
        // Extract email addresses
        const emailRegex = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g;
        const emails = message.match(emailRegex);
        if (emails && emails.length > 0) {
            this.userInfo.email = emails[0];
        }

        // Extract phone numbers (Indian format)
        const phoneRegex = /(?:\+91|91)?[-.\s]?[6-9]\d{9}/g;
        const phones = message.match(phoneRegex);
        if (phones && phones.length > 0) {
            this.userInfo.phone = phones[0].replace(/[-.\s]/g, '');
        }

        // Extract names (simple heuristic)
        const namePatterns = [
            /my name is ([a-zA-Z\s]+)/i,
            /i am ([a-zA-Z\s]+)/i,
            /this is ([a-zA-Z\s]+)/i
        ];
        
        for (const pattern of namePatterns) {
            const match = message.match(pattern);
            if (match && match[1]) {
                const fullName = match[1].trim();
                const nameParts = fullName.split(' ');
                this.userInfo.first_name = nameParts[0];
                if (nameParts.length > 1) {
                    this.userInfo.last_name = nameParts.slice(1).join(' ');
                }
                break;
            }
        }
    }

    async sendConversationToCRM() {
        // Only send if there was meaningful conversation (more than just welcome message)
        if (this.conversationHistory.length < 2) {
            return;
        }

        try {
            const conversationData = {
                session_id: this.sessionId,
                user_messages: this.conversationHistory
                    .filter(msg => msg.role === 'user')
                    .map(msg => msg.text),
                bot_responses: this.conversationHistory
                    .filter(msg => msg.role === 'assistant')
                    .map(msg => msg.text),
                user_info: this.userInfo,
                conversation_context: {
                    total_messages: this.conversationHistory.length,
                    session_duration: Date.now() - parseInt(this.sessionId.split('_')[1]),
                    timestamp: new Date().toISOString()
                }
            };

            // Send to CRM API (invisible to user)
            const response = await fetch('/api/integrations/webhooks/chatbot/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(conversationData)
            });

            if (response.ok) {
                console.log('Conversation data sent to CRM successfully');
            } else {
                console.warn('Failed to send conversation data to CRM:', response.status);
            }
        } catch (error) {
            // Silently handle errors - don't disrupt user experience
            console.warn('Error sending conversation data to CRM:', error);
        }
    }

    getCSRFToken() {
        // Get CSRF token from cookie or meta tag
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='))
            ?.split('=')[1];
        
        if (cookieValue) {
            return cookieValue;
        }

        // Fallback: get from meta tag
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
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
