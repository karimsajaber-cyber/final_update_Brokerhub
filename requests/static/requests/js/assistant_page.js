(function () {
    const chatBox = document.getElementById('chat-box');
    const input = document.getElementById('chat-input');
    const sendButton = document.getElementById('chat-send');
    const resultsArea = document.getElementById('results-area');
    const resultsContainer = document.getElementById('results-container');
    const initialPayloadNode = document.getElementById('assistant-initial-payload');

    if (!chatBox || !input || !sendButton || !resultsArea || !resultsContainer) {
        return;
    }

    const colorMap = {
        Amazon: { bg: '#fff3e0', color: '#d97706', label: 'Amazon' },
        Shein: { bg: '#fce7f3', color: '#be185d', label: 'Shein' },
        Temu: { bg: '#dbeafe', color: '#1d4ed8', label: 'Temu' },
    };

    const platformSearch = {
        Amazon: (name) => `https://www.amazon.com/s?k=${encodeURIComponent(name)}`,
        Shein: (name) => `https://www.shein.com/search?q=${encodeURIComponent(name)}`,
        Temu: (name) => `https://www.temu.com/search?q=${encodeURIComponent(name)}`,
    };

    let conversationHistory = [];

    function escapeHtml(value) {
        return String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function scrollToBottom() {
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function addMessage(type, content) {
        const isAI = type === 'ai';
        const wrapper = document.createElement('div');
        wrapper.className = `msg-bubble ${isAI ? 'msg-bubble-ai' : 'msg-bubble-user'}`;
        wrapper.innerHTML = `
            <div class="${isAI ? 'ai-avatar' : 'user-avatar'}">${isAI ? 'AI' : 'You'}</div>
            <div class="${isAI ? 'ai-bubble' : 'user-bubble'}">
                <p>${escapeHtml(content)}</p>
            </div>
        `;
        chatBox.appendChild(wrapper);
        scrollToBottom();
    }

    function addTyping() {
        const wrapper = document.createElement('div');
        wrapper.id = 'typing-indicator';
        wrapper.className = 'msg-bubble msg-bubble-ai';
        wrapper.innerHTML = `
            <div class="ai-avatar">AI</div>
            <div class="ai-bubble">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
        `;
        chatBox.appendChild(wrapper);
        scrollToBottom();
    }

    function removeTyping() {
        const node = document.getElementById('typing-indicator');
        if (node) {
            node.remove();
        }
    }

    function getCookie(name) {
        let value = null;
        document.cookie.split(';').forEach((entry) => {
            const trimmed = entry.trim();
            if (trimmed.startsWith(`${name}=`)) {
                value = decodeURIComponent(trimmed.split('=')[1]);
            }
        });
        return value;
    }

    function renderBrokerList(list, brokers, productName, productUrl) {
        list.innerHTML = brokers.map((broker) => {
            const imageUrl = broker.profile_image_url || broker.image_url;
            const brokerName = broker.display_name || broker.name || 'Broker';
            const brokerCity = broker.city ? `${escapeHtml(broker.city)} &middot; ` : '';
            const brokerRating = typeof broker.rating === 'number' ? broker.rating.toFixed(1) : '0.0';
            const avatarHtml = imageUrl
                ? `<span class="assistant-broker-avatar"><img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(brokerName)}"></span>`
                : `<span class="assistant-broker-avatar">${escapeHtml(brokerName.charAt(0).toUpperCase())}</span>`;

            return `
                <button type="button" class="assistant-broker-btn" data-broker-id="${broker.id}" data-product-name="${escapeHtml(productName)}" data-product-url="${escapeHtml(productUrl)}">
                    ${avatarHtml}
                    <div>
                        <strong>${escapeHtml(brokerName)}</strong>
                        <span>${brokerCity}&#9733; ${brokerRating}</span>
                    </div>
                </button>
            `;
        }).join('');

        list.querySelectorAll('.assistant-broker-btn').forEach((button) => {
            button.addEventListener('click', () => {
                selectBroker(
                    button.getAttribute('data-broker-id'),
                    button.getAttribute('data-product-name'),
                    button.getAttribute('data-product-url')
                );
            });
        });
    }

    function closeBrokerModal() {
        const existing = document.getElementById('broker-modal');
        if (existing) {
            existing.remove();
        }
    }

    function showBrokerModal(productName, productUrl, detectedCategory) {
        closeBrokerModal();

        const modal = document.createElement('div');
        modal.id = 'broker-modal';
        modal.className = 'assistant-modal';
        modal.innerHTML = `
            <div class="assistant-modal-card">
                <h3>Choose a broker</h3>
                <p>Select who should handle <strong>${escapeHtml(productName)}</strong>.</p>
                <div id="broker-list" class="assistant-modal-list">
                    <p>Loading brokers...</p>
                </div>
                <button type="button" class="assistant-modal-cancel" id="assistant-modal-cancel">Cancel</button>
            </div>
        `;

        document.body.appendChild(modal);
        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                closeBrokerModal();
            }
        });
        document.getElementById('assistant-modal-cancel').addEventListener('click', closeBrokerModal);

        const apiUrl = detectedCategory
            ? `/api/brokers/?category=${encodeURIComponent(detectedCategory)}`
            : '/api/brokers/';

        fetch(apiUrl)
            .then((response) => response.json())
            .then((data) => {
                const list = document.getElementById('broker-list');
                if (!data.brokers || data.brokers.length === 0) {
                    if (detectedCategory) {
                        fetch('/api/brokers/')
                            .then((response) => response.json())
                            .then((fallback) => renderBrokerList(list, fallback.brokers || [], productName, productUrl));
                        return;
                    }

                    list.innerHTML = '<p>No brokers found right now.</p>';
                    return;
                }

                renderBrokerList(list, data.brokers, productName, productUrl);
            })
            .catch(() => {
                document.getElementById('broker-list').innerHTML = '<a href="/brokers" class="assistant-request-btn" style="text-decoration:none;">Browse brokers</a>';
            });
    }

    function selectBroker(brokerId, productName, productUrl) {
        closeBrokerModal();
        const finalUrl = productUrl || `https://www.amazon.com/s?k=${encodeURIComponent(productName)}`;
        window.location.href = `/create?broker_id=${encodeURIComponent(brokerId)}&prefill_name=${encodeURIComponent(productName)}&prefill_url=${encodeURIComponent(finalUrl)}`;
    }

    function resetResults() {
        resultsContainer.innerHTML = '';
        resultsArea.hidden = true;
    }

    function showResults(data) {
        if (!data.has_results) {
            resetResults();
            return;
        }

        let minPrice = Number.POSITIVE_INFINITY;
        let cheapest = '';
        data.results.forEach((item) => {
            const value = parseFloat(String(item.price || '').replace('$', '').replace(',', ''));
            if (!Number.isNaN(value) && value < minPrice) {
                minPrice = value;
                cheapest = item.platform;
            }
        });

        const grouped = {};
        data.results.forEach((item) => {
            if (!grouped[item.platform]) {
                grouped[item.platform] = item;
            }
        });

        let html = `
            <div class="assistant-result-heading">
                <h4 class="assistant-results-title">Results for "${escapeHtml(data.product_name)}"</h4>
                <p class="assistant-results-subtitle">Cheapest option: <strong>${escapeHtml(cheapest || 'Unavailable')}</strong>${Number.isFinite(minPrice) ? ` at $${minPrice.toFixed(2)}` : ''}</p>
            </div>
        `;

        Object.values(grouped).forEach((item) => {
            const palette = colorMap[item.platform] || { bg: '#eef2ff', color: '#4f46e5', label: item.platform || 'Store' };
            const fallbackUrlBuilder = platformSearch[item.platform] || platformSearch.Amazon;
            const viewUrl = item.url && item.url.length > 5 ? item.url : fallbackUrlBuilder(item.name || data.product_name);
            const isCheapest = item.platform === cheapest;
            const productName = item.name || data.product_name;
            const safeProductName = escapeHtml(productName);
            const safeUrl = escapeHtml(viewUrl);
            const safeCategory = escapeHtml(data.detected_category || '');
            const safeNote = item.note ? `<p class="assistant-result-note">${escapeHtml(item.note)}</p>` : '';
            const imageHtml = item.image
                ? `<img src="${escapeHtml(item.image)}" alt="${safeProductName}">`
                : `<span class="assistant-result-fallback">${escapeHtml(palette.label.charAt(0))}</span>`;

            html += `
                <article class="assistant-result-card ${isCheapest ? 'is-cheapest' : ''}">
                    <div class="assistant-result-top">
                        <span class="assistant-result-platform" style="background:${palette.bg};color:${palette.color};">${escapeHtml(palette.label)}</span>
                        ${isCheapest ? '<span class="assistant-result-highlight">Cheapest</span>' : ''}
                    </div>
                    <div class="assistant-result-image">${imageHtml}</div>
                    <p class="assistant-result-name">${safeProductName}</p>
                    <p class="assistant-result-price">${escapeHtml(item.price || 'N/A')}</p>
                    ${safeNote}
                    <div class="assistant-result-actions">
                        <a href="${safeUrl}" target="_blank" rel="noopener noreferrer" class="assistant-action">View product</a>
                        <button type="button" class="assistant-request-btn" data-product-name="${safeProductName}" data-product-url="${safeUrl}" data-category="${safeCategory}">Request broker</button>
                    </div>
                </article>
            `;
        });

        html += `
            <div class="assistant-summary-card">
                <h4>Need help buying it?</h4>
                <p>Open a request and let brokers compete for the best offer.</p>
                <a href="/brokers" class="assistant-action">Browse brokers</a>
            </div>
        `;

        resultsContainer.innerHTML = html;
        resultsArea.hidden = false;
        resultsContainer.querySelectorAll('.assistant-request-btn').forEach((button) => {
            button.addEventListener('click', () => {
                showBrokerModal(
                    button.getAttribute('data-product-name'),
                    button.getAttribute('data-product-url'),
                    button.getAttribute('data-category')
                );
            });
        });
    }

    async function sendSearch(message, type) {
        addMessage('user', message);
        input.value = '';
        addTyping();
        conversationHistory.push({ role: 'user', content: message });

        try {
            const response = await fetch(chatSearchUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({
                    message,
                    type: type || 'chat',
                    history: conversationHistory,
                    source: 'assistant_page',
                }),
            });

            const data = await response.json();
            removeTyping();

            if (data.type === 'search') {
                addMessage('ai', data.ai_summary || 'Here are the results I found.');
                showResults(data);
                conversationHistory = [];
                return;
            }

            addMessage('ai', data.message || 'Tell me more about the product you want.');
            conversationHistory.push({ role: 'assistant', content: data.message || '' });
        } catch (error) {
            removeTyping();
            addMessage('ai', 'Sorry, something went wrong. Please try again.');
        }
    }

    function sendMessage() {
        const message = input.value.trim();
        if (message) {
            sendSearch(message, 'chat');
        }
    }

    sendButton.addEventListener('click', sendMessage);
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            sendMessage();
        }
    });

    document.querySelectorAll('.assistant-page .cat-btn').forEach((button) => {
        button.addEventListener('click', () => {
            conversationHistory = [];
            sendSearch(button.dataset.category || button.textContent.trim(), 'chat');
        });
    });

    if (initialPayloadNode && initialPayloadNode.textContent.trim()) {
        try {
            const initialPayload = JSON.parse(initialPayloadNode.textContent);
            if (initialPayload && initialPayload.has_results) {
                addMessage('user', initialPayload.original_message || initialPayload.product_name);
                addMessage('ai', initialPayload.ai_summary || 'Here are the results I found.');
                showResults(initialPayload);
            }
        } catch (error) {
            resetResults();
        }
    }
})();
