(function () {
    const root = document.getElementById("faq-edit-api");
    if (!root) {
        return;
    }

    const reorderUrl = root.dataset.reorderUrl;
    const createUrl = root.dataset.createUrl;
    const detailUrlTemplate = root.dataset.detailUrlTemplate;
    const detailPkPlaceholder = root.dataset.detailPkPlaceholder || "987654321";
    const draftLabel = root.dataset.draftLabel || "Draft";

    function getCsrfToken() {
        const name = "csrftoken";
        if (document.cookie && document.cookie !== "") {
            const parts = document.cookie.split(";");
            for (let i = 0; i < parts.length; i++) {
                const cookie = parts[i].trim();
                if (cookie.substring(0, name.length + 1) === name + "=") {
                    return decodeURIComponent(cookie.substring(name.length + 1));
                }
            }
        }
        return "";
    }

    function detailUrl(id) {
        return detailUrlTemplate.split(detailPkPlaceholder).join(String(id));
    }

    function parseEntriesJson() {
        const el = document.getElementById("faq-entries-json");
        if (!el || !el.textContent) {
            return [];
        }
        try {
            const data = JSON.parse(el.textContent);
            return Array.isArray(data) ? data : [];
        } catch {
            return [];
        }
    }

    let entriesById = {};
    parseEntriesJson().forEach(function (e) {
        entriesById[e.id] = e;
    });

    const accordionEl = document.getElementById("faqAccordion");
    const modalEl = document.getElementById("faqEntryModal");
    const modal =
        modalEl && window.bootstrap && window.bootstrap.Modal
            ? window.bootstrap.Modal.getOrCreateInstance(modalEl)
            : null;
    const questionInput = document.getElementById("faqQuestionInput");
    const answerInput = document.getElementById("faqAnswerInput");
    const publishedInput = document.getElementById("faqPublishedInput");
    const formErrorEl = document.getElementById("faqFormError");
    const saveBtn = document.getElementById("faqSaveBtn");
    const addBtn = document.getElementById("faqAddBtn");
    const modalTitle = document.getElementById("faqEntryModalLabel");

    let editingId = null;

    function showFormError(msg) {
        if (!formErrorEl) {
            return;
        }
        formErrorEl.textContent = msg;
        formErrorEl.classList.remove("d-none");
    }

    function clearFormError() {
        if (!formErrorEl) {
            return;
        }
        formErrorEl.textContent = "";
        formErrorEl.classList.add("d-none");
    }

    function openModalForCreate() {
        editingId = null;
        if (modalTitle) {
            modalTitle.textContent = modalTitle.dataset.addTitle || "";
        }
        questionInput.value = "";
        answerInput.value = "";
        publishedInput.checked = true;
        clearFormError();
        if (modal) {
            modal.show();
        }
    }

    function openModalForEdit(id) {
        editingId = id;
        const entry = entriesById[id];
        if (!entry) {
            return;
        }
        if (modalTitle) {
            modalTitle.textContent = modalTitle.dataset.editTitle || "";
        }
        questionInput.value = entry.question;
        answerInput.value = entry.answer;
        publishedInput.checked = entry.is_published;
        clearFormError();
        if (modal) {
            modal.show();
        }
    }

    async function apiJson(url, method, body) {
        const headers = {
            "X-CSRFToken": getCsrfToken(),
            "Content-Type": "application/json",
        };
        const opts = { method, headers, credentials: "same-origin" };
        if (body !== undefined) {
            opts.body = JSON.stringify(body);
        }
        const res = await fetch(url, opts);
        let data = {};
        const text = await res.text();
        if (text) {
            try {
                data = JSON.parse(text);
            } catch {
                data = { error: text };
            }
        }
        if (!res.ok) {
            const err = new Error(data.error || res.statusText || "Request failed");
            err.status = res.status;
            err.data = data;
            throw err;
        }
        return data;
    }

    function updateEntryInDom(entry) {
        const item = document.querySelector(
            '.faq-accordion-item[data-entry-id="' + entry.id + '"]'
        );
        if (!item) {
            return;
        }
        const qEl = item.querySelector(".faq-question-text");
        if (qEl) {
            qEl.textContent = entry.question;
        }
        const aEl = item.querySelector(".faq-answer-text");
        if (aEl) {
            aEl.textContent = entry.answer;
        }
        const btn = item.querySelector(".accordion-button");
        if (btn) {
            let badge = btn.querySelector(".badge");
            if (entry.is_published) {
                if (badge) {
                    badge.remove();
                }
            } else if (!badge) {
                const span = document.createElement("span");
                span.className = "badge bg-secondary ms-2";
                span.textContent = draftLabel;
                btn.appendChild(span);
            }
        }
        entriesById[entry.id] = entry;
    }

    function removeEntryFromDom(id) {
        const item = document.querySelector(
            '.faq-accordion-item[data-entry-id="' + id + '"]'
        );
        if (item) {
            item.remove();
        }
        delete entriesById[id];
        const staffEmpty = document.getElementById("faqStaffEmptyMsg");
        if (accordionEl && accordionEl.children.length === 0 && staffEmpty) {
            staffEmpty.classList.remove("d-none");
        }
    }

    if (saveBtn && modal) {
        saveBtn.addEventListener("click", async function () {
            clearFormError();
            const payload = {
                question: questionInput.value.trim(),
                answer: answerInput.value,
                is_published: publishedInput.checked,
            };
            try {
                if (editingId === null) {
                    await apiJson(createUrl, "POST", payload);
                    window.location.reload();
                    return;
                }
                const data = await apiJson(detailUrl(editingId), "PATCH", payload);
                if (data.entry) {
                    updateEntryInDom(data.entry);
                }
                modal.hide();
            } catch (e) {
                if (e.data && e.data.errors) {
                    showFormError(JSON.stringify(e.data.errors));
                } else {
                    showFormError(e.message || "Error");
                }
            }
        });
    }

    if (addBtn && modal) {
        addBtn.addEventListener("click", function () {
            openModalForCreate();
        });
    }

    document.querySelectorAll(".faq-edit-btn").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const id = parseInt(btn.getAttribute("data-entry-id"), 10);
            openModalForEdit(id);
        });
    });

    document.querySelectorAll(".faq-delete-btn").forEach(function (btn) {
        btn.addEventListener("click", async function () {
            const id = parseInt(btn.getAttribute("data-entry-id"), 10);
            if (!window.confirm(btn.getAttribute("data-confirm") || "Delete this entry?")) {
                return;
            }
            try {
                await apiJson(detailUrl(id), "DELETE");
                removeEntryFromDom(id);
                if (accordionEl && accordionEl.children.length === 0) {
                    window.location.reload();
                }
            } catch (e) {
                window.alert(e.message || "Delete failed");
            }
        });
    });

    if (accordionEl && typeof Sortable !== "undefined") {
        Sortable.create(accordionEl, {
            animation: 150,
            handle: ".faq-drag-handle",
            draggable: ".faq-accordion-item",
            onEnd: async function () {
                const ids = [];
                accordionEl.querySelectorAll(".faq-accordion-item").forEach(function (el) {
                    ids.push(parseInt(el.getAttribute("data-entry-id"), 10));
                });
                try {
                    await apiJson(reorderUrl, "POST", { order: ids });
                } catch (e) {
                    window.alert(e.message || "Could not save order");
                    window.location.reload();
                }
            },
        });
    }

    if (modalTitle) {
        modalTitle.dataset.addTitle = modalTitle.getAttribute("data-add-title") || "";
        modalTitle.dataset.editTitle = modalTitle.getAttribute("data-edit-title") || "";
    }
})();

