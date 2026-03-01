document.addEventListener('DOMContentLoaded', () => {
    const topicInput = document.getElementById('topic-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('messages');
    const chatContainer = document.getElementById('chat-container');
    const suggestionsContainer = document.getElementById('suggested-prompts-container');

    function addMessage(content, isUser = false, originalQuery = null, isRawHtml = false) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${isUser ? 'user-message' : 'ai-message'}`;

        if (isUser) {
            msgDiv.textContent = content;
        } else {
            if (isRawHtml) {
                msgDiv.innerHTML = content;
            } else {
                // Render markdown using Marked.js
                msgDiv.innerHTML = marked.parse(content);
            }

            // Add media actions if it's an AI message and we have an original query
            if (originalQuery) {
                const actionsDiv = document.createElement('div');
                actionsDiv.className = 'media-actions';

                // Audio Button
                const audioBtn = document.createElement('button');
                audioBtn.className = 'media-btn';
                audioBtn.innerHTML = '🔊 Audio Summary';
                audioBtn.onclick = () => generateAudio(audioBtn, actionsDiv, originalQuery);

                // Video Button
                const videoBtn = document.createElement('button');
                videoBtn.className = 'media-btn';
                videoBtn.innerHTML = '🎬 Generate Explainer Video';
                videoBtn.onclick = () => generateVideo(videoBtn, actionsDiv, originalQuery);

                actionsDiv.appendChild(audioBtn);
                actionsDiv.appendChild(videoBtn);
                msgDiv.appendChild(actionsDiv);
            }
        }

        messagesContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        return msgDiv;
    }

    async function generateAudio(btn, container, query) {
        btn.disabled = true;
        btn.innerHTML = '<div class="loading" style="width:16px;height:16px;border-width:2px;margin-right:5px"></div> Generating...';

        try {
            const res = await fetch('/api/generate_audio', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();

            if (data.error) {
                alert("Audio error: " + data.error);
                btn.innerHTML = '🔊 Retry Audio';
                btn.disabled = false;
                return;
            }

            btn.style.display = 'none'; // hide button, show player

            const playerDiv = document.createElement('div');
            playerDiv.className = 'media-player';
            playerDiv.innerHTML = `
                <p style="font-size:0.9rem; color:#94a3b8; margin-bottom:5px;"><strong>Summary:</strong> ${data.summary}</p>
                <audio controls autoplay src="${data.audio_url}"></audio>
            `;
            container.appendChild(playerDiv);
            chatContainer.scrollTop = chatContainer.scrollHeight;

        } catch (err) {
            alert("Network error: " + err);
            btn.innerHTML = '🔊 Retry Audio';
            btn.disabled = false;
        }
    }

    async function generateVideo(btn, container, query) {
        btn.disabled = true;
        btn.innerHTML = '<div class="loading" style="width:16px;height:16px;border-width:2px;margin-right:5px"></div> Starting...';

        try {
            const res = await fetch('/api/generate_video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });
            const data = await res.json();

            if (data.error) {
                alert("Video error: " + data.error);
                btn.innerHTML = '🎬 Retry Video';
                btn.disabled = false;
                return;
            }

            btn.innerHTML = '<div class="loading" style="width:16px;height:16px;border-width:2px;margin-right:5px"></div> Waiting for Veo 3...';
            pollVideoStatus(data.operation_id, btn, container);

        } catch (err) {
            alert("Network error: " + err);
            btn.innerHTML = '🎬 Retry Video';
            btn.disabled = false;
        }
    }

    async function pollVideoStatus(operationId, btn, container) {
        try {
            const res = await fetch(`/api/video_status/${operationId}`);
            const data = await res.json();

            if (data.status === 'running') {
                setTimeout(() => pollVideoStatus(operationId, btn, container), 5000); // poll every 5s
            } else if (data.status === 'done') {
                btn.style.display = 'none';
                const playerDiv = document.createElement('div');
                playerDiv.className = 'media-player';
                playerDiv.innerHTML = `
                    <video controls autoplay loop src="${data.video_url}"></video>
                `;
                container.appendChild(playerDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            } else {
                alert("Video generation failed: " + data.error);
                btn.innerHTML = '🎬 Retry Video';
                btn.disabled = false;
            }
        } catch (err) {
            alert("Polling error: " + err);
            btn.innerHTML = '🎬 Retry Video';
            btn.disabled = false;
        }
    }

    async function handleSend() {
        const query = topicInput.value.trim();
        if (!query) return;

        // Display user message
        addMessage(query, true);
        topicInput.value = '';
        suggestionsContainer.innerHTML = ''; // clear suggestions
        document.getElementById('generate-deck-btn').style.display = 'inline-block';

        // Disable input while generating
        topicInput.disabled = true;
        sendBtn.disabled = true;

        // Add loading indicator
        const loadingMsg = addMessage('<div class="loading"></div> Thinking & calling Imagen 4...');

        try {
            const response = await fetch('/api/explain', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query })
            });

            const data = await response.json();

            // Remove loading msg
            loadingMsg.remove();

            if (data.error) {
                addMessage(`**Error:** ${data.error}`);
            } else {
                let aiText = data.text;
                let presentationUrl = null;

                // Check for presentation deck URL
                const presMatch = aiText.match(/\/presentation\/[0-9a-fA-F-]+/);
                if (presMatch) {
                    presentationUrl = presMatch[0];
                    aiText = aiText.replace(presentationUrl, ''); // remove from normal flow
                }

                const msgDiv = addMessage(aiText, false, query);

                if (presentationUrl) {
                    const presBtn = document.createElement('a');
                    presBtn.href = presentationUrl;
                    presBtn.target = "_blank";
                    presBtn.className = 'media-btn presentation-btn';
                    presBtn.style.display = "inline-block";
                    presBtn.style.marginTop = "10px";
                    presBtn.style.textDecoration = "none";
                    presBtn.innerHTML = '📊 View Presentation Deck';

                    // append it to the actions div if it exists, otherwise to message
                    const actionsDiv = msgDiv.querySelector('.media-actions');
                    if (actionsDiv) {
                        actionsDiv.appendChild(presBtn);
                    } else {
                        msgDiv.appendChild(presBtn);
                    }
                }

                // Render suggestions if any
                if (data.suggestions && data.suggestions.length > 0) {
                    data.suggestions.forEach(suggestion => {
                        const btn = document.createElement('button');
                        btn.className = 'suggestion-btn';
                        btn.textContent = suggestion;
                        btn.onclick = () => {
                            topicInput.value = suggestion;
                            handleSend();
                        };
                        suggestionsContainer.appendChild(btn);
                    });
                }
            }
        } catch (err) {
            loadingMsg.remove();
            addMessage(`**Network Error:** Could not reach the server.`);
            console.error(err);
        } finally {
            topicInput.disabled = false;
            sendBtn.disabled = false;
            topicInput.focus();
        }
    }

    async function requestPresentation() {
        const btn = document.getElementById('generate-deck-btn');
        const originalText = btn.innerHTML;

        btn.innerHTML = "⏳ Structuring slides...";
        btn.disabled = true;

        const prompt = "Please summarize our entire lesson into a presentation deck using the create_presentation_deck tool. Keep the text concise and use previously generated media.";

        try {
            const response = await fetch('/api/explain', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: prompt })
            });

            const data = await response.json();

            const urlMatch = data.text ? data.text.match(/\/presentation\/[a-zA-Z0-9-]+/) : null;

            if (urlMatch) {
                const presentationUrl = urlMatch[0];

                const htmlContent = `
                    <div style="padding: 15px; border-radius: 8px; text-align: center; margin-top: 10px;">
                        <h3 style="margin-top: 0;">🎉 Your Deck is Ready!</h3>
                        <p>I've compiled our lesson into an interactive presentation.</p>
                        <a href="${presentationUrl}" target="_blank" style="
                            display: inline-block;
                            background: #28a745;
                            color: white;
                            padding: 10px 20px;
                            text-decoration: none;
                            border-radius: 5px;
                            font-weight: bold;
                            margin-top: 10px;
                        ">📺 Open Presentation</a>
                    </div>
                `;
                // pass true for isRawHtml
                addMessage(htmlContent, false, null, true);
            } else {
                addMessage("Could not generate the presentation. Please try asking directly in the chat.", false);
            }
        } catch (error) {
            console.error("Error generating deck:", error);
            addMessage("An error occurred while building the deck.", false);
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }

    sendBtn.addEventListener('click', handleSend);
    topicInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSend();
        }
    });

    const generateDeckBtn = document.getElementById('generate-deck-btn');
    if (generateDeckBtn) {
        generateDeckBtn.addEventListener('click', requestPresentation);
    }
});
