(function () {
    const app = document.getElementById("chatApp");
    if (!app) {
        return;
    }

    const fetchUrl = app.dataset.fetchUrl;
    const sendUrl = app.dataset.sendUrl;
    const reportUrl = app.dataset.reportUrl;
    const messagesList = document.getElementById("messagesList");
    const chatForm = document.getElementById("chatForm");
    const chatInput = document.getElementById("chatInput");
    const reportModal = document.getElementById("reportModal");
    const reportForm = document.getElementById("reportForm");
    const reportMessageId = document.getElementById("reportMessageId");
    const reportReason = document.getElementById("reportReason");
    const reportFeedback = document.getElementById("reportFeedback");
    const csrfToken = chatForm.querySelector("[name=csrfmiddlewaretoken]").value;

    let latestMessageId = 0;
    let isFirstLoad = true;

    function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value;
        return div.innerHTML;
    }

    function scrollToBottom(force) {
        const distanceFromBottom = messagesList.scrollHeight - messagesList.scrollTop - messagesList.clientHeight;
        if (force || distanceFromBottom < 120) {
            messagesList.scrollTop = messagesList.scrollHeight;
        }
    }

    function renderMessage(message) {
        latestMessageId = Math.max(latestMessageId, message.id);

        const wrapper = document.createElement("article");
        wrapper.className = "chat-message" + (message.is_mine ? " is-mine" : "");
        wrapper.dataset.messageId = message.id;

        const reportButton = message.can_report
            ? '<button type="button" class="chat-report-btn" data-report-id="' + message.id + '">Report</button>'
            : "";
        const readLabel = message.is_mine ? (message.is_read ? "Read" : "Sent") : "";

        wrapper.innerHTML = [
            '<div class="chat-message__bubble">' + escapeHtml(message.content) + "</div>",
            '<div class="chat-message__meta">',
            "<span>" + escapeHtml(message.timestamp) + "</span>",
            readLabel ? "<span>" + escapeHtml(readLabel) + "</span>" : "",
            reportButton,
            "</div>",
        ].join("");

        messagesList.appendChild(wrapper);
    }

    function loadMessages() {
        const url = latestMessageId ? fetchUrl + "?after_id=" + latestMessageId : fetchUrl;
        fetch(url, {
            headers: {
                "X-Requested-With": "XMLHttpRequest",
            },
        })
            .then((response) => response.json())
            .then((data) => {
                if (!data.messages || !data.messages.length) {
                    return;
                }

                data.messages.forEach(renderMessage);
                scrollToBottom(isFirstLoad);
                isFirstLoad = false;
            })
            .catch(() => {});
    }

    function openReportModal(messageId) {
        reportMessageId.value = messageId;
        reportReason.value = "";
        reportFeedback.textContent = "";
        reportFeedback.className = "report-feedback";
        reportModal.hidden = false;
    }

    function closeReportModal() {
        reportModal.hidden = true;
    }

    chatForm.addEventListener("submit", function (event) {
        event.preventDefault();
        const content = chatInput.value.trim();
        if (!content) {
            chatInput.focus();
            return;
        }

        const formData = new FormData();
        formData.append("content", content);

        fetch(sendUrl, {
            method: "POST",
            headers: {
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest",
            },
            body: formData,
        })
            .then((response) => response.json().then((data) => ({ ok: response.ok, data: data })))
            .then(({ ok, data }) => {
                if (!ok || !data.message) {
                    return;
                }

                renderMessage(data.message);
                chatInput.value = "";
                scrollToBottom(true);
            })
            .catch(() => {});
    });

    messagesList.addEventListener("click", function (event) {
        const button = event.target.closest("[data-report-id]");
        if (!button) {
            return;
        }
        openReportModal(button.dataset.reportId);
    });

    reportForm.addEventListener("submit", function (event) {
        event.preventDefault();

        fetch(reportUrl, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
                "X-Requested-With": "XMLHttpRequest",
            },
            body: JSON.stringify({
                message_id: reportMessageId.value,
                reason: reportReason.value.trim(),
            }),
        })
            .then((response) => response.json().then((data) => ({ ok: response.ok, data: data })))
            .then(({ ok, data }) => {
                reportFeedback.textContent = data.message || data.error || "";
                reportFeedback.className = "report-feedback " + (ok ? "is-success" : "is-error");
                if (ok) {
                    window.setTimeout(closeReportModal, 900);
                }
            })
            .catch(() => {
                reportFeedback.textContent = "Unable to send the report right now.";
                reportFeedback.className = "report-feedback is-error";
            });
    });

    document.querySelectorAll("[data-close-report]").forEach(function (element) {
        element.addEventListener("click", closeReportModal);
    });

    loadMessages();
    window.setInterval(loadMessages, 3000);
})();
