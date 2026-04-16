(function () {
    const widget = document.getElementById('assistant-widget');
    const overlay = document.getElementById('assistant-overlay');
    const launcher = document.getElementById('assistant-launcher');
    const panel = document.getElementById('assistant-panel');
    const closeButton = document.getElementById('assistant-close');
    const expandButton = document.getElementById('assistant-expand');
    const chatBox = document.getElementById('chat-box');
    const input = document.getElementById('chat-input');
    const sendButton = document.getElementById('chat-send');
    const resultsArea = document.getElementById('results-area');
    const resultsContainer = document.getElementById('results-container');
    const categories = document.getElementById('assistant-categories');
    const panelBody = panel ? panel.querySelector('.assistant-panel-body') : null;

    if (!widget || !overlay || !launcher || !panel || !closeButton || !expandButton || !chatBox || !input || !sendButton || !resultsArea || !resultsContainer || !categories || !panelBody) {
        console.log('missing element');
        return;
    }

    const colorMap = {
        Amazon: { bg: '#fff3e0', color: '#d97706', emoji: '&#128717;&#65039;' },
        Shein: { bg: '#fce7f3', color: '#be185d', emoji: '&#128087;' },
        Temu: { bg: '#dbeafe', color: '#1d4ed8', emoji: '&#128722;' },
    };

    const platformSearch = {
        Amazon: (name) => `https://www.amazon.com/s?k=${encodeURIComponent(name)}`,
        Shein: (name) => `https://www.shein.com/search?q=${encodeURIComponent(name)}`,
        Temu: (name) => `https://www.temu.com/search?q=${encodeURIComponent(name)}`,
    };

    const state = {
        visible: false,
        open: false,
        fullscreen: false,
        history: [],
        hasInteracted: false,
        userScrolledUp: false,
    };

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function isNearBottom() {
        return panelBody.scrollHeight - panelBody.scrollTop - panelBody.clientHeight <= 48;
    }

    function scrollPanelToBottom() {
        // نجيب عنصر الرسائل مباشرة (أضمن من panelBody)
        const el = document.querySelector('.assistant-panel-body');
        if (!el) return;

        // لو المستخدم طالع لفوق لا نزعجه
        if (state && state.userScrolledUp) return;

        // سكرول فوري + إعادة تثبيت بعد الرسم
        el.scrollTop = el.scrollHeight;
        requestAnimationFrame(() => {
            el.scrollTop = el.scrollHeight;
        });
    }

    function maybeScrollToBottom(shouldAutoScroll) {
        if (!shouldAutoScroll) {
            return;
        }

        state.userScrolledUp = false;
        requestAnimationFrame(scrollPanelToBottom);
    }

    function showBubble() {
        state.visible = true;
        renderState({ focusInput: false });
    }

    function renderState(options = {}) {
        widget.classList.toggle('is-visible', state.visible);
        widget.classList.toggle('is-open', state.open);
        widget.classList.toggle('is-fullscreen', state.fullscreen);

        launcher.setAttribute('aria-expanded', String(state.open));
        panel.setAttribute('aria-hidden', String(!state.open));
        overlay.setAttribute('aria-hidden', String(!state.fullscreen));
        expandButton.setAttribute('aria-label', state.fullscreen ? 'Restore assistant size' : 'Expand assistant');
        expandButton.innerHTML = state.fullscreen ? '&#11123;' : '&#9723;';

        if (state.open && options.focusInput !== false) {
            window.setTimeout(() => {
                input.focus();
            }, options.delay == null ? 220 : options.delay);
        }
    }

    function openChat(options = {}) {
        state.visible = true;
        state.open = true;
        renderState(options);
    }

    function minimizeChat() {
        state.open = false;
        state.fullscreen = false;
        renderState({ focusInput: false });
    }

    function toggleFullscreen() {
        state.fullscreen = !state.fullscreen;
        openChat({ delay: 120 });
    }

    function resetResults() {
        resultsContainer.innerHTML = '';
        resultsArea.hidden = true;
    }

    function revealCategories() {
        if (state.hasInteracted) {
            return;
        }

        state.hasInteracted = true;
        categories.classList.remove('is-hidden');
    }

    function addMessage(type, content) {
        const shouldAutoScroll = true;
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
        maybeScrollToBottom(shouldAutoScroll);
    }

    function addTyping() {
        const shouldAutoScroll = true;
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
        maybeScrollToBottom(shouldAutoScroll);
    }

    function removeTyping() {
        const node = document.getElementById('typing-indicator');
        if (node) {
            node.remove();
        }
    }

    function renderBrokerList(list, brokers, productName, productUrl) {
        list.innerHTML = brokers.map((broker) => {
            const imageUrl = broker.profile_image_url || broker.image_url;
            const avatarHtml = imageUrl
                ? `<span class="assistant-broker-avatar"><img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(broker.display_name || broker.name || 'Broker')}"></span>`
                : `<span class="assistant-broker-avatar">${escapeHtml((broker.display_name || broker.name || 'B').charAt(0).toUpperCase())}</span>`;
            const brokerName = broker.display_name || broker.name || 'Broker';
            const brokerCity = broker.city ? `${escapeHtml(broker.city)} &middot; ` : '';
            const brokerRating = typeof broker.rating === 'number' ? broker.rating.toFixed(1) : '0.0';

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
        const destination = `/create?broker_id=${encodeURIComponent(brokerId)}&prefill_name=${encodeURIComponent(productName)}&prefill_url=${encodeURIComponent(finalUrl)}`;
        window.location.href = destination;
    }

    function showResults(data) {
        const shouldAutoScroll = isNearBottom();

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
            const palette = colorMap[item.platform] || { bg: '#eef2ff', color: '#4f46e5', emoji: '&#128722;' };
            const fallbackUrlBuilder = platformSearch[item.platform] || platformSearch.Amazon;
            const viewUrl = item.url && item.url.length > 5 ? item.url : fallbackUrlBuilder(item.name || data.product_name);
            const isCheapest = item.platform === cheapest;
            const safeProductName = escapeHtml(item.name || data.product_name);
            const safeUrl = escapeHtml(viewUrl);
            const safeCategory = escapeHtml(data.detected_category || '');
            const safeNote = item.note ? `<p class="assistant-result-note">${escapeHtml(item.note)}</p>` : '';
            const imageHtml = item.image
                ? `<img src="${escapeHtml(item.image)}" alt="${safeProductName}">`
                : `<span class="assistant-result-fallback">${palette.emoji}</span>`;

            html += `
                <article class="assistant-result-card ${isCheapest ? 'is-cheapest' : ''}">
                    <div class="assistant-result-top">
                        <span class="assistant-result-platform" style="background:${palette.bg};color:${palette.color};">${palette.emoji} ${escapeHtml(item.platform)}</span>
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
                minimizeChat();
                showBrokerModal(
                    button.getAttribute('data-product-name'),
                    button.getAttribute('data-product-url'),
                    button.getAttribute('data-category')
                );
            });
        });

        maybeScrollToBottom(shouldAutoScroll);
        state.history = [];
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

    async function sendMessage() {
        const message = input.value.trim();
        if (!message) {
            return;
        }

        openChat({ focusInput: false });
        revealCategories();
        resetResults();
        addMessage('user', message);
        input.value = '';
        addTyping();
        state.history.push({ role: 'user', content: message });

        try {
            const response = await fetch(chatSearchUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ message, type: 'chat', history: state.history }),
            });

            const data = await response.json();
            removeTyping();

            if (data.type === 'search') {
                if (data.has_results && data.assistant_redirect_url) {
                    window.location.href = data.assistant_redirect_url;
                    return;
                }
                addMessage('ai', data.ai_summary || 'Here are the results I found.');
                showResults(data);
            } else {
                addMessage('ai', data.message || 'Tell me more about the product you want.');
                state.history.push({ role: 'assistant', content: data.message || '' });
            }
        } catch (error) {
            removeTyping();
            addMessage('ai', 'Sorry, something went wrong. Please try again.');
        }
    }

    async function categorySearch(category, emoji) {
        openChat({ focusInput: false });
        state.history = [];
        revealCategories();
        categories.classList.add('is-hidden');
        resetResults();
        addMessage('user', `${emoji} ${category}`);
        addTyping();
        state.history.push({ role: 'user', content: category });

        try {
            const response = await fetch(chatSearchUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ message: category, type: 'chat', history: state.history }),
            });

            const data = await response.json();
            removeTyping();

            if (data.type === 'search') {
                if (data.has_results && data.assistant_redirect_url) {
                    window.location.href = data.assistant_redirect_url;
                    return;
                }
                addMessage('ai', data.ai_summary || 'Here are the results I found.');
                showResults(data);
            } else {
                addMessage('ai', data.message || `What ${category} product are you looking for?`);
                state.history.push({ role: 'assistant', content: data.message || '' });
            }
        } catch (error) {
            removeTyping();
            addMessage('ai', `What ${category} product are you looking for?`);
        }
    }

    launcher.addEventListener('click', () => openChat());
    closeButton.addEventListener('click', minimizeChat);
    expandButton.addEventListener('click', toggleFullscreen);
    overlay.addEventListener('click', () => {
        if (state.fullscreen) {
            state.fullscreen = false;
            renderState({ focusInput: false });
        }
    });
    sendButton.addEventListener('click', sendMessage);
    input.addEventListener('focus', revealCategories);
    input.addEventListener('click', revealCategories);
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            sendMessage();
        }
    });

    panelBody.addEventListener('scroll', () => {
        state.userScrolledUp = !isNearBottom();
    });

    panel.querySelectorAll('.cat-btn').forEach((button) => {
        button.addEventListener('click', () => {
            categorySearch(button.dataset.category, button.dataset.emoji);
        });
    });

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Escape') {
            return;
        }

        if (state.fullscreen) {
            state.fullscreen = false;
            renderState({ focusInput: false });
            return;
        }

        if (state.open) {
            minimizeChat();
        }
    });

    renderState({ focusInput: false });

    window.addEventListener('load', () => {
        const shouldAutoOpen = widget.dataset.autoOpen === 'true'
            || (typeof chatbotAutoOpen !== 'undefined' && chatbotAutoOpen);

        window.setTimeout(() => {
            if (shouldAutoOpen) {
                openChat({ focusInput: false });
                return;
            }

            showBubble();
        }, 1000);
    });
})();
