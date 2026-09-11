// Chatbot state
let chatContext = {};

// DOM Elements
const chatTrigger = document.getElementById('chatbot-trigger');
const chatModal = document.getElementById('chatbot-modal');
const chatClose = document.querySelector('.chatbot-close');
const chatMessages = document.getElementById('chatbot-messages');
const chatInput = document.getElementById('chatbot-input');
const chatSend = document.getElementById('chatbot-send');
const chatOptions = document.getElementById('chatbot-options');

// CSRF Token for Django
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
const csrftoken = getCookie('csrftoken');

// Event Listeners
chatTrigger.addEventListener('click', toggleChat);
chatClose.addEventListener('click', toggleChat);
chatSend.addEventListener('click', handleSendMessage);
chatInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        handleSendMessage();
    }
});

// Toggle chat modal
function toggleChat() {
    chatModal.classList.toggle('active');
    if (chatModal.classList.contains('active')) {
        chatInput.focus();
        // Initialize chat if it's the first time
        if (chatMessages.children.length === 0) {
            initializeChat();
        }
    }
}

// Initialize chat
function initializeChat() {
    // Send an 'init' message to the backend to get the welcome message and initial options
    sendToBackend('init');
}

// Add a message to the chat
function addMessage(content, isUser = false) {
    const messagesContainer = document.getElementById('chatbot-messages');
    if (!messagesContainer) {
        console.error('Messages container not found!');
        return;
    }
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user-message' : 'bot-message'}`;
    
    if (isUser) {
        messageDiv.textContent = content;
    } else {
        messageDiv.innerHTML = content; // Use innerHTML for bot messages to render formatting
    }
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
    // Force reflow to ensure the message is visible
    void messageDiv.offsetHeight;
}

// Add a bot message
function addBotMessage(text) {
    addMessage(text, false);
}

// Show options to the user
function showOptions(options) {
    chatOptions.innerHTML = '';
    if (!options || options.length === 0) return;
    
    options.forEach(option => {
        const button = document.createElement('button');
        button.className = 'option-btn';
        button.textContent = option;
        button.addEventListener('click', () => {
            processUserInput(option);
        });
        chatOptions.appendChild(button);
    });
}

// Send message to backend
function sendToBackend(message) {
    fetch('/chat/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({
            message: message,
            context: chatContext
        })
    })
    .then(response => response.json())
    .then(data => {
        // Update context
        chatContext = data.context || {};
        
        // Add bot response
        if (data.message) {
            addBotMessage(data.message);
        }
        
        // Show options if any
        if (data.options && data.options.length > 0) {
            showOptions(data.options);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        addBotMessage('Sorry, there was an error processing your request. Please try again.');
    });
}

// Process user input
function processUserInput(input) {
    // Add user message to chat
    addMessage(input, true);
    
    // Clear options
    chatOptions.innerHTML = '';

    // Clear input field
    chatInput.value = '';
    
    // Send to backend
    sendToBackend(input);
}

// Send message from input field
function handleSendMessage() {
    const message = chatInput.value.trim();
    if (message) {
        processUserInput(message);
    }
}

// Close chat when clicking outside
window.addEventListener('click', (e) => {
    if (e.target === chatModal) {
        toggleChat();
    }
});
