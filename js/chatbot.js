const tarangChatbotStyles = `
#tarang-chat-widget {
    position: fixed;
    bottom: 20px;
    right: 20px;
    z-index: 9999;
    font-family: 'Inter', sans-serif;
}
#tarang-chat-button {
    width: 60px;
    height: 60px;
    border-radius: 30px;
    background-color: #0ea5e9;
    color: white;
    border: none;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: transform 0.2s;
}
#tarang-chat-button:hover {
    transform: scale(1.05);
}
#tarang-chat-button svg {
    width: 28px;
    height: 28px;
    fill: currentColor;
}
#tarang-chat-window {
    display: none;
    width: 350px;
    height: 500px;
    background: white;
    border-radius: 12px;
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    position: absolute;
    bottom: 80px;
    right: 0;
    flex-direction: column;
    overflow: hidden;
    border: 1px solid #e2e8f0;
}
#tarang-chat-header {
    background: #0ea5e9;
    color: white;
    padding: 16px;
    font-weight: 600;
    display: flex;
    justify-content: space-between;
    align-items: center;
}
#tarang-chat-header button {
    background: none;
    border: none;
    color: white;
    cursor: pointer;
    font-size: 20px;
}
#tarang-chat-messages {
    flex: 1;
    padding: 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
    background: #f8fafc;
}
.chat-message {
    max-width: 85%;
    padding: 10px 14px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.4;
}
.chat-message.user {
    background: #0ea5e9;
    color: white;
    align-self: flex-end;
    border-bottom-right-radius: 2px;
}
.chat-message.bot {
    background: white;
    color: #334155;
    align-self: flex-start;
    border: 1px solid #e2e8f0;
    border-bottom-left-radius: 2px;
}
#tarang-chat-input-area {
    padding: 12px;
    background: white;
    border-top: 1px solid #e2e8f0;
    display: flex;
    gap: 8px;
}
#tarang-chat-input {
    flex: 1;
    padding: 10px 14px;
    border: 1px solid #cbd5e1;
    border-radius: 20px;
    outline: none;
    font-size: 14px;
}
#tarang-chat-input:focus {
    border-color: #0ea5e9;
}
#tarang-chat-send {
    background: #0ea5e9;
    color: white;
    border: none;
    width: 40px;
    height: 40px;
    border-radius: 20px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
}
#tarang-chat-send:disabled {
    background: #cbd5e1;
    cursor: not-allowed;
}
.typing-indicator {
    display: flex;
    gap: 4px;
    padding: 12px 14px;
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    align-self: flex-start;
    border-bottom-left-radius: 2px;
}
.typing-dot {
    width: 6px;
    height: 6px;
    background: #94a3b8;
    border-radius: 50%;
    animation: typing 1.4s infinite ease-in-out;
}
.typing-dot:nth-child(1) { animation-delay: -0.32s; }
.typing-dot:nth-child(2) { animation-delay: -0.16s; }
@keyframes typing {
    0%, 80%, 100% { transform: scale(0); }
    40% { transform: scale(1); }
}
`;

document.addEventListener('DOMContentLoaded', () => {
    const styleEl = document.createElement('style');
    styleEl.textContent = tarangChatbotStyles;
    document.head.appendChild(styleEl);

    const widgetHtml = `
        <div id="tarang-chat-widget">
            <button id="tarang-chat-button" aria-label="Open Chat">
                <svg viewBox="0 0 24 24"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H5.2L4 17.2V4h16v12z"/></svg>
            </button>
            <div id="tarang-chat-window">
                <div id="tarang-chat-header">
                    <span>TARANG AI</span>
                    <button id="tarang-chat-close" style="font-size: 24px; line-height: 1; background:none; border:none; color:white; cursor:pointer;">&times;</button>
                </div>
                <div id="tarang-chat-messages">
                    <div class="chat-message bot" id="tarang-lang-prompt">
                        Please select your preferred language:<br>
                        कृपया अपनी पसंदीदा भाषा चुनें:<br>
                        உங்கள் விருப்பமான மொழியைத் தேர்ந்தெடுக்கவும்:<br><br>
                        <div style="display:flex; gap:8px; flex-direction:column; margin-top:8px;">
                            <button class="lang-btn" data-lang="english" style="padding:8px; border:1px solid #0ea5e9; border-radius:4px; background:white; color:#0ea5e9; cursor:pointer;">English</button>
                            <button class="lang-btn" data-lang="hindi" style="padding:8px; border:1px solid #0ea5e9; border-radius:4px; background:white; color:#0ea5e9; cursor:pointer;">हिंदी (Hindi)</button>
                            <button class="lang-btn" data-lang="tamil" style="padding:8px; border:1px solid #0ea5e9; border-radius:4px; background:white; color:#0ea5e9; cursor:pointer;">தமிழ் (Tamil)</button>
                        </div>
                    </div>
                </div>
                <form id="tarang-chat-input-area" style="display:none;">
                    <input type="text" id="tarang-chat-input" placeholder="Type your message..." autocomplete="off">
                    <button type="submit" id="tarang-chat-send">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
                    </button>
                </form>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', widgetHtml);

    const button = document.getElementById('tarang-chat-button');
    const chatWindow = document.getElementById('tarang-chat-window');
    const closeBtn = document.getElementById('tarang-chat-close');
    const messages = document.getElementById('tarang-chat-messages');
    const inputForm = document.getElementById('tarang-chat-input-area');
    const input = document.getElementById('tarang-chat-input');
    const sendBtn = document.getElementById('tarang-chat-send');

    let isOpen = false;
    let selectedLang = 'english';

    const intros = {
        english: "Hello! I'm the TARANG AI Assistant. I can help answer any questions about the TARANG Marine Intelligence Platform, operations, and workflow. How can I assist you today?",
        hindi: "नमस्ते! मैं तरंग एआई सहायक हूं। मैं तरंग समुद्री खुफिया मंच, संचालन और कार्यप्रवाह के बारे में किसी भी प्रश्न का उत्तर देने में मदद कर सकता हूं। मैं आज आपकी कैसे सहायता कर सकता हूं?",
        tamil: "வணக்கம்! நான் தரங் AI உதவியாளர். தரங் மரைன் நுண்ணறிவு தளம், செயல்பாடுகள் மற்றும் பணிப்பாய்வு பற்றிய எந்த கேள்விகளுக்கும் பதிலளிக்க நான் உதவ முடியும். இன்று நான் உங்களுக்கு எப்படி உதவ முடியும்?"
    };

    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            selectedLang = e.target.getAttribute('data-lang');
            document.getElementById('tarang-lang-prompt').style.display = 'none';
            addMessage(intros[selectedLang], 'bot');
            inputForm.style.display = 'flex';
        });
    });

    button.addEventListener('click', () => {
        isOpen = !isOpen;
        chatWindow.style.display = isOpen ? 'flex' : 'none';
        if (isOpen) input.focus();
    });

    closeBtn.addEventListener('click', () => {
        isOpen = false;
        chatWindow.style.display = 'none';
    });

    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `chat-message ${sender}`;
        div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function showTyping() {
        const div = document.createElement('div');
        div.className = 'typing-indicator';
        div.id = 'typing-indicator';
        div.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function hideTyping() {
        const el = document.getElementById('typing-indicator');
        if (el) el.remove();
    }

    inputForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;

        input.value = '';
        input.disabled = true;
        sendBtn.disabled = true;

        addMessage(text, 'user');
        showTyping();

        try {
            const res = await fetch('/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text, language: selectedLang })
            });
            const data = await res.json();
            hideTyping();
            if (data.reply) {
                addMessage(data.reply, 'bot');
            } else {
                addMessage("I'm sorry, I'm having trouble connecting to the server.", 'bot');
            }
        } catch (err) {
            hideTyping();
            addMessage("An error occurred while sending your message.", 'bot');
        } finally {
            input.disabled = false;
            sendBtn.disabled = false;
            input.focus();
        }
    });

    // ==========================================
    // SIMULATION WIDGET
    // ==========================================
    const simWidgetHtml = `
        <div id="tarang-sim-widget">
            <button id="tarang-sim-button" style="position: fixed; bottom: 100px; right: 24px; width: 56px; height: 56px; border-radius: 28px; background: #14B8A6; color: white; border: none; box-shadow: 0 4px 12px rgba(20,184,166,0.3); cursor: pointer; display: flex; align-items: center; justify-content: center; z-index: 9998;" title="Open Seabed Simulation">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
            </button>
            <div id="tarang-sim-modal" style="display: none; position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(2,11,21,0.95); z-index: 10000; align-items: center; justify-content: center; backdrop-filter: blur(10px);">
                <div style="position: relative; width: 95vw; height: 95vh; background: #000; border-radius: 12px; overflow: hidden; border: 1px solid #14B8A6; box-shadow: 0 0 40px rgba(20,184,166,0.2);">
                    <div style="position: absolute; top: 16px; right: 16px; z-index: 10001; display: flex; gap: 12px; align-items: center;">
                        <span style="color: #14B8A6; font-family: monospace; font-size: 14px; font-weight: bold; background: rgba(0,0,0,0.6); padding: 4px 12px; border-radius: 4px; border: 1px solid #14B8A6;">LIVE SIMULATION</span>
                        <button id="tarang-sim-close" style="background: rgba(0,0,0,0.8); border: 1px solid #14B8A6; color: white; width: 40px; height: 40px; border-radius: 8px; cursor: pointer; font-size: 24px; display: flex; align-items: center; justify-content: center; transition: all 0.2s;">&times;</button>
                    </div>
                    <iframe src="/simulation/" style="width: 100%; height: 100%; border: none;"></iframe>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', simWidgetHtml);

    const simButton = document.getElementById('tarang-sim-button');
    const simModal = document.getElementById('tarang-sim-modal');
    const simCloseBtn = document.getElementById('tarang-sim-close');

    simButton.addEventListener('click', () => {
        simModal.style.display = 'flex';
        simCloseBtn.addEventListener('mouseenter', () => simCloseBtn.style.background = '#14B8A6');
        simCloseBtn.addEventListener('mouseleave', () => simCloseBtn.style.background = 'rgba(0,0,0,0.8)');
    });

    simCloseBtn.addEventListener('click', () => {
        simModal.style.display = 'none';
    });
});

