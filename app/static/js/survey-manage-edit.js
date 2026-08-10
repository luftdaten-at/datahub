(function () {
    "use strict";

    const root = document.getElementById("survey-question-api");
    if (!root) {
        return;
    }

    const createUrl = root.dataset.createUrl;
    const reorderUrl = root.dataset.reorderUrl;
    const detailUrlTemplate = root.dataset.detailUrlTemplate;
    const detailPkPlaceholder = root.dataset.detailPkPlaceholder || "987654321";
    const labels = {
        required: root.dataset.labelRequired || "Required",
        edit: root.dataset.labelEdit || "Edit",
        delete: root.dataset.labelDelete || "Delete",
        dragTitle: root.dataset.labelDragTitle || "Drag to reorder",
        empty: root.dataset.labelEmpty || "No questions yet.",
        deleteConfirm: root.dataset.labelDeleteConfirm || "Delete this question?",
        deleteFailed: root.dataset.labelDeleteFailed || "Delete failed",
        labelRequired: root.dataset.labelLabelRequired || "Label is required.",
        validationFailed: root.dataset.labelValidationFailed || "Validation failed",
        requestFailed: root.dataset.labelRequestFailed || "Request failed",
        reorderFailed: root.dataset.labelReorderFailed || "Could not save order",
        pageBreak: root.dataset.labelPageBreak || "Page break",
        pageBreakHint:
            root.dataset.labelPageBreakHint ||
            "Optional page title for the following page",
        pageNum: root.dataset.labelPageNum || "Page %(num)s",
        startsPage: root.dataset.labelStartsPage || "Starts page %(num)s",
        pagesSummary: root.dataset.labelPagesSummary || "%(count)s page(s)",
    };

    const TYPE_TEXT = "text";
    const TYPE_RANGE = "range";
    const TYPE_LIKERT = "likert";
    const TYPE_SINGLE_CHOICE = "single_choice";
    const TYPE_MULTIPLE_CHOICE = "multiple_choice";
    const TYPE_MAP_POINTS = "map_points";
    const TYPE_PAGE_BREAK = "page_break";

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

    function parseQuestionsJson() {
        const el = document.getElementById("survey-questions-json");
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

    let questionsById = {};
    parseQuestionsJson().forEach(function (q) {
        questionsById[q.id] = q;
    });

    const listEl = document.getElementById("surveyQuestionsList");
    const modalEl = document.getElementById("questionModal");
    const modal =
        modalEl && window.bootstrap && window.bootstrap.Modal
            ? window.bootstrap.Modal.getOrCreateInstance(modalEl)
            : null;
    const modalTitle = document.getElementById("questionModalLabel");
    const formErrorEl = document.getElementById("questionFormError");
    const addBtn = document.getElementById("questionAddBtn");
    const pageBreakAddBtn = document.getElementById("pageBreakAddBtn");
    const pagesSummaryEl = document.getElementById("surveyPagesSummary");
    const saveBtn = document.getElementById("questionSaveBtn");
    const typeInput = document.getElementById("questionTypeInput");
    const labelInput = document.getElementById("questionLabelInput");
    const labelHelpEl = document.getElementById("questionLabelHelp");
    const helpInput = document.getElementById("questionHelpInput");
    const helpRow = document.getElementById("questionHelpRow");
    const requiredInput = document.getElementById("questionRequiredInput");
    const requiredRow = document.getElementById("questionRequiredRow");
    const configRange = document.getElementById("configRange");
    const configLikert = document.getElementById("configLikert");
    const configChoiceOptions = document.getElementById("configChoiceOptions");
    const configMapPoints = document.getElementById("configMapPoints");
    const configRangeMin = document.getElementById("configRangeMin");
    const configRangeMax = document.getElementById("configRangeMax");
    const configLikertScale = document.getElementById("configLikertScale");
    const configMapMaxPoints = document.getElementById("configMapMaxPoints");
    const mapCategoriesEditor = document.getElementById("mapCategoriesEditor");
    const choiceOptionsEditor = document.getElementById("choiceOptionsEditor");
    const choiceOptionAddBtn = document.getElementById("choiceOptionAddBtn");
    const configMapPointChoicesMode = document.getElementById("configMapPointChoicesMode");
    const configMapPointChoicesHelp = document.getElementById("configMapPointChoicesHelp");
    const mapPointChoicesEditor = document.getElementById("mapPointChoicesEditor");
    const mapPointChoiceAddBtn = document.getElementById("mapPointChoiceAddBtn");

    let editingId = null;

    if (modalTitle) {
        modalTitle.dataset.addTitle = modalTitle.getAttribute("data-add-title") || "";
        modalTitle.dataset.editTitle = modalTitle.getAttribute("data-edit-title") || "";
    }

    function showFormError(msg) {
        if (!formErrorEl) return;
        formErrorEl.textContent = msg;
        formErrorEl.classList.remove("d-none");
    }

    function clearFormError() {
        if (!formErrorEl) return;
        formErrorEl.textContent = "";
        formErrorEl.classList.add("d-none");
    }

    function isPageBreak(type) {
        return type === TYPE_PAGE_BREAK;
    }

    function displayLabel(q) {
        if (q.label) {
            return q.label;
        }
        if (q.question_type === TYPE_PAGE_BREAK) {
            return labels.pageBreak;
        }
        return "";
    }

    function updateTypeSpecificFields(type) {
        updateConfigPanel(type);
        if (isPageBreak(type)) {
            if (helpRow) helpRow.classList.add("d-none");
            if (requiredRow) requiredRow.classList.add("d-none");
            if (requiredInput) requiredInput.checked = false;
            if (labelHelpEl) labelHelpEl.textContent = labels.pageBreakHint;
        } else {
            if (helpRow) helpRow.classList.remove("d-none");
            if (requiredRow) requiredRow.classList.remove("d-none");
            if (labelHelpEl) labelHelpEl.textContent = "";
        }
    }

    function isChoiceType(type) {
        return type === TYPE_SINGLE_CHOICE || type === TYPE_MULTIPLE_CHOICE;
    }

    function updateConfigPanel(type) {
        [configRange, configLikert, configChoiceOptions, configMapPoints].forEach(function (el) {
            if (el) el.classList.add("d-none");
        });
        if (type === TYPE_RANGE && configRange) {
            configRange.classList.remove("d-none");
        } else if (type === TYPE_LIKERT && configLikert) {
            configLikert.classList.remove("d-none");
        } else if (isChoiceType(type) && configChoiceOptions) {
            configChoiceOptions.classList.remove("d-none");
        } else if (type === TYPE_MAP_POINTS && configMapPoints) {
            configMapPoints.classList.remove("d-none");
        }
    }

    function readConfigFromForm(type) {
        if (type === TYPE_RANGE) {
            return {
                min: parseFloat(configRangeMin.value),
                max: parseFloat(configRangeMax.value),
            };
        }
        if (type === TYPE_LIKERT) {
            return { scale: parseInt(configLikertScale.value, 10) };
        }
        if (isChoiceType(type)) {
            return { options: readOptionsFromEditor(choiceOptionsEditor) };
        }
        if (type === TYPE_MAP_POINTS) {
            const config = {
                max_points: parseInt(configMapMaxPoints.value, 10),
                categories: readCategoriesFromEditor(),
            };
            const pointChoices = readMapPointChoicesFromEditor();
            if (pointChoices) {
                config.point_choices = pointChoices;
            }
            return config;
        }
        return {};
    }

    function readMapPointChoicesFromEditor() {
        const options = readOptionsFromEditor(mapPointChoicesEditor);
        if (!options.length) {
            return null;
        }
        const mode = configMapPointChoicesMode
            ? configMapPointChoicesMode.value
            : "single";
        const helpText = configMapPointChoicesHelp
            ? configMapPointChoicesHelp.value.trim()
            : "";
        const result = { mode: mode, options: options };
        if (helpText) {
            result.help_text = helpText;
        }
        return result;
    }

    function readOptionsFromEditor(editorEl) {
        if (!editorEl) return [];
        const rows = editorEl.querySelectorAll(".choice-option-row");
        const options = [];
        rows.forEach(function (row) {
            const value = ((row.querySelector(".choice-option-label") || {}).value || "").trim();
            if (value) {
                options.push(value);
            }
        });
        return options;
    }

    function renderOptionRows(options, editorEl) {
        if (!editorEl) return;
        editorEl.innerHTML = "";
        const list = options && options.length ? options : ["", ""];
        list.forEach(function (option) {
            const row = document.createElement("div");
            row.className = "choice-option-row border rounded p-2 mb-2";
            row.innerHTML =
                '<div class="row g-2 align-items-center">' +
                '<div class="col"><input type="text" class="form-control form-control-sm choice-option-label" placeholder="Option label" value="' +
                escapeHtml(option || "") +
                '"></div>' +
                '<div class="col-auto"><button type="button" class="btn btn-sm btn-outline-danger choice-option-remove-btn">&times;</button></div>' +
                "</div>";
            const removeBtn = row.querySelector(".choice-option-remove-btn");
            if (removeBtn) {
                removeBtn.addEventListener("click", function () {
                    row.remove();
                    if (!editorEl.querySelector(".choice-option-row")) {
                        renderOptionRows(["", ""], editorEl);
                    }
                });
            }
            editorEl.appendChild(row);
        });
    }

    function fillOptionsForm(options) {
        renderOptionRows(options && options.length ? options : ["", ""], choiceOptionsEditor);
    }

    function fillMapPointChoicesForm(pointChoices) {
        pointChoices = pointChoices || {};
        if (configMapPointChoicesMode) {
            configMapPointChoicesMode.value = pointChoices.mode || "single";
        }
        if (configMapPointChoicesHelp) {
            configMapPointChoicesHelp.value = pointChoices.help_text || "";
        }
        renderOptionRows(
            pointChoices.options && pointChoices.options.length ? pointChoices.options : [],
            mapPointChoicesEditor
        );
    }

    function defaultCategoryRow() {
        return { key: "", label: "", color: "#3388ff" };
    }

    function readCategoriesFromEditor() {
        if (!mapCategoriesEditor) return [];
        const row = mapCategoriesEditor.querySelector(".map-category-row");
        if (!row) return [];
        return [{
            key: (row.querySelector(".map-category-key") || {}).value || "",
            label: (row.querySelector(".map-category-label") || {}).value || "",
            color: (row.querySelector(".map-category-color") || {}).value || "#3388ff",
        }];
    }

    function renderCategoryRow(category) {
        if (!mapCategoriesEditor) return;
        const cat = category || defaultCategoryRow();
        mapCategoriesEditor.innerHTML =
            '<div class="map-category-row border rounded p-2 mb-2">' +
            '<div class="row g-2 align-items-center">' +
            '<div class="col-md-3"><input type="text" class="form-control form-control-sm map-category-key" placeholder="key" value="' +
            escapeHtml(cat.key || "") +
            '"></div>' +
            '<div class="col-md-4"><input type="text" class="form-control form-control-sm map-category-label" placeholder="Label" value="' +
            escapeHtml(cat.label || "") +
            '"></div>' +
            '<div class="col-md-3"><input type="color" class="form-control form-control-color map-category-color" value="' +
            escapeHtml(cat.color || "#3388ff") +
            '"></div>' +
            "</div></div>";
    }

    function fillCategoriesForm(categories) {
        const category = categories && categories.length ? categories[0] : defaultCategoryRow();
        renderCategoryRow(category);
    }

    function fillConfigForm(type, config) {
        config = config || {};
        if (type === TYPE_RANGE) {
            configRangeMin.value = config.min !== undefined ? config.min : 0;
            configRangeMax.value = config.max !== undefined ? config.max : 10;
        } else if (type === TYPE_LIKERT) {
            configLikertScale.value = config.scale !== undefined ? config.scale : 5;
        } else if (isChoiceType(type)) {
            fillOptionsForm(config.options || []);
        } else if (type === TYPE_MAP_POINTS) {
            configMapMaxPoints.value =
                config.max_points !== undefined ? config.max_points : 50;
            fillCategoriesForm(config.categories || []);
            fillMapPointChoicesForm(config.point_choices || null);
        }
    }

    function formatErrors(errors) {
        if (typeof errors === "string") return errors;
        if (errors && errors.__all__) {
            return Array.isArray(errors.__all__) ? errors.__all__.join(" ") : errors.__all__;
        }
        if (errors && errors.config) {
            return Array.isArray(errors.config) ? errors.config.join(" ") : errors.config;
        }
        try {
            return JSON.stringify(errors);
        } catch {
            return labels.validationFailed;
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
        const resp = await fetch(url, opts);
        let data = null;
        try {
            data = await resp.json();
        } catch {
            data = null;
        }
        if (!resp.ok) {
            const err = new Error(
                data && data.error ? data.error : labels.requestFailed
            );
            err.data = data;
            throw err;
        }
        return data;
    }

    function removeEmptyState() {
        const empty = document.getElementById("surveyQuestionsEmpty");
        if (empty) empty.remove();
    }

    function formatLabel(template, replacements) {
        let text = template || "";
        Object.keys(replacements).forEach(function (key) {
            text = text.split("%(" + key + ")s").join(String(replacements[key]));
        });
        return text;
    }

    function refreshPageNumbers() {
        if (!listEl) return;
        let page = 1;
        let maxPage = 1;
        const items = listEl.querySelectorAll(".question-item");
        items.forEach(function (item) {
            const type = item.getAttribute("data-question-type");
            const badge = item.querySelector(".question-page-badge");
            if (isPageBreak(type)) {
                page += 1;
                maxPage = Math.max(maxPage, page);
                if (badge) {
                    badge.textContent = formatLabel(labels.startsPage, { num: page });
                    badge.classList.remove("d-none");
                }
            } else {
                maxPage = Math.max(maxPage, page);
                if (badge) {
                    badge.textContent = formatLabel(labels.pageNum, { num: page });
                    badge.classList.remove("d-none");
                }
            }
        });
        if (pagesSummaryEl) {
            if (items.length === 0) {
                pagesSummaryEl.textContent = "";
            } else {
                pagesSummaryEl.textContent = formatLabel(labels.pagesSummary, {
                    count: maxPage,
                });
            }
        }
    }

    function buildQuestionItem(q) {
        const item = document.createElement("div");
        item.className =
            "list-group-item question-item d-flex align-items-start gap-2" +
            (isPageBreak(q.question_type)
                ? " question-page-break border border-2 border-dashed"
                : "");
        item.setAttribute("data-question-id", String(q.id));
        item.setAttribute("data-question-type", q.question_type);

        const badgeClass = isPageBreak(q.question_type)
            ? "badge text-bg-info"
            : "badge text-bg-secondary";
        const requiredBadge = q.required
            ? '<span class="badge text-bg-warning">' + escapeHtml(labels.required) + "</span>"
            : "";
        const categoryBadge =
            q.question_type === TYPE_MAP_POINTS && q.config && q.config.categories && q.config.categories.length
                ? '<span class="badge text-bg-light border">' +
                  escapeHtml(q.config.categories[0].label || q.config.categories[0].key || "") +
                  "</span>"
                : "";
        const optionsBadge =
            isChoiceType(q.question_type) && q.config && q.config.options
                ? '<span class="badge text-bg-light border">' +
                  escapeHtml(String(q.config.options.length)) +
                  " opt.</span>"
                : "";
        const pointChoicesBadge =
            q.question_type === TYPE_MAP_POINTS &&
            q.config &&
            q.config.point_choices &&
            q.config.point_choices.options &&
            q.config.point_choices.options.length
                ? '<span class="badge text-bg-light border">' +
                  escapeHtml(String(q.config.point_choices.options.length)) +
                  " detail opt.</span>"
                : "";
        const helpHtml = q.help_text
            ? '<div class="small text-muted">' + escapeHtml(q.help_text) + "</div>"
            : "";

        item.innerHTML =
            '<span class="question-drag-handle text-muted pt-1" title="' +
            escapeHtml(labels.dragTitle) +
            '" aria-hidden="true">⋮⋮</span>' +
            '<div class="flex-grow-1">' +
            '<div class="d-flex flex-wrap align-items-center gap-2 mb-1">' +
            '<span class="' +
            badgeClass +
            '">' +
            escapeHtml(q.question_type_display || q.question_type) +
            "</span>" +
            '<span class="badge text-bg-light border question-page-badge"></span>' +
            requiredBadge +
            categoryBadge +
            optionsBadge +
            pointChoicesBadge +
            "</div>" +
            '<div class="fw-semibold">' +
            escapeHtml(displayLabel(q)) +
            "</div>" +
            helpHtml +
            "</div>" +
            '<div class="btn-group btn-group-sm">' +
            '<button type="button" class="btn btn-outline-secondary question-edit-btn" data-question-id="' +
            q.id +
            '">' +
            escapeHtml(labels.edit) +
            "</button>" +
            '<button type="button" class="btn btn-outline-danger question-delete-btn" data-question-id="' +
            q.id +
            '">' +
            escapeHtml(labels.delete) +
            "</button>" +
            "</div>";

        bindItemButtons(item);
        return item;
    }

    function escapeHtml(text) {
        const div = document.createElement("div");
        div.textContent = text || "";
        return div.innerHTML;
    }

    function bindItemButtons(item) {
        const editBtn = item.querySelector(".question-edit-btn");
        const deleteBtn = item.querySelector(".question-delete-btn");
        if (editBtn) {
            editBtn.addEventListener("click", function () {
                openModalForEdit(parseInt(editBtn.getAttribute("data-question-id"), 10));
            });
        }
        if (deleteBtn) {
            deleteBtn.addEventListener("click", function () {
                deleteQuestion(parseInt(deleteBtn.getAttribute("data-question-id"), 10));
            });
        }
    }

    function updateQuestionInDom(q) {
        questionsById[q.id] = q;
        const existing = listEl.querySelector('[data-question-id="' + q.id + '"]');
        const item = buildQuestionItem(q);
        if (existing) {
            existing.replaceWith(item);
        } else {
            removeEmptyState();
            listEl.appendChild(item);
        }
        refreshPageNumbers();
    }

    function removeQuestionFromDom(id) {
        delete questionsById[id];
        const existing = listEl.querySelector('[data-question-id="' + id + '"]');
        if (existing) existing.remove();
        if (listEl.querySelectorAll(".question-item").length === 0) {
            const empty = document.createElement("div");
            empty.id = "surveyQuestionsEmpty";
            empty.className = "text-muted py-3";
            empty.textContent = labels.empty;
            listEl.appendChild(empty);
        }
        refreshPageNumbers();
    }

    function openModalForCreate() {
        editingId = null;
        if (modalTitle) {
            modalTitle.textContent = modalTitle.dataset.addTitle || labels.edit;
        }
        typeInput.value = TYPE_TEXT;
        labelInput.value = "";
        helpInput.value = "";
        requiredInput.checked = false;
        fillConfigForm(TYPE_TEXT, {});
        updateTypeSpecificFields(TYPE_TEXT);
        clearFormError();
        if (modal) modal.show();
    }

    function openModalForCreatePageBreak() {
        editingId = null;
        if (modalTitle) {
            modalTitle.textContent = labels.pageBreak;
        }
        typeInput.value = TYPE_PAGE_BREAK;
        labelInput.value = "";
        helpInput.value = "";
        requiredInput.checked = false;
        fillConfigForm(TYPE_PAGE_BREAK, {});
        updateTypeSpecificFields(TYPE_PAGE_BREAK);
        clearFormError();
        if (modal) modal.show();
    }

    function openModalForEdit(id) {
        const q = questionsById[id];
        if (!q) return;
        editingId = id;
        if (modalTitle) {
            modalTitle.textContent = modalTitle.dataset.editTitle || labels.edit;
        }
        typeInput.value = q.question_type;
        labelInput.value = q.label || "";
        helpInput.value = q.help_text || "";
        requiredInput.checked = !!q.required;
        fillConfigForm(q.question_type, q.config);
        updateTypeSpecificFields(q.question_type);
        clearFormError();
        if (modal) modal.show();
    }

    async function deleteQuestion(id) {
        if (!window.confirm(labels.deleteConfirm)) return;
        try {
            await apiJson(detailUrl(id), "DELETE");
            removeQuestionFromDom(id);
        } catch (e) {
            window.alert(e.message || labels.deleteFailed);
        }
    }

    if (typeInput) {
        typeInput.addEventListener("change", function () {
            updateTypeSpecificFields(typeInput.value);
            if (typeInput.value === TYPE_MAP_POINTS && mapCategoriesEditor &&
                !mapCategoriesEditor.querySelector(".map-category-row")) {
                fillCategoriesForm([]);
            }
            if (typeInput.value === TYPE_MAP_POINTS && mapPointChoicesEditor &&
                !mapPointChoicesEditor.querySelector(".choice-option-row")) {
                fillMapPointChoicesForm(null);
            }
            if (isChoiceType(typeInput.value) && choiceOptionsEditor &&
                !choiceOptionsEditor.querySelector(".choice-option-row")) {
                fillOptionsForm([]);
            }
        });
    }

    if (choiceOptionAddBtn) {
        choiceOptionAddBtn.addEventListener("click", function () {
            const current = readOptionsFromEditor(choiceOptionsEditor);
            current.push("");
            renderOptionRows(current, choiceOptionsEditor);
        });
    }

    if (mapPointChoiceAddBtn) {
        mapPointChoiceAddBtn.addEventListener("click", function () {
            const current = readOptionsFromEditor(mapPointChoicesEditor);
            current.push("");
            renderOptionRows(current.length ? current : ["", ""], mapPointChoicesEditor);
        });
    }

    if (addBtn) {
        addBtn.addEventListener("click", openModalForCreate);
    }

    if (pageBreakAddBtn) {
        pageBreakAddBtn.addEventListener("click", openModalForCreatePageBreak);
    }

    listEl.querySelectorAll(".question-item").forEach(function (item) {
        bindItemButtons(item);
    });
    refreshPageNumbers();

    if (saveBtn) {
        saveBtn.addEventListener("click", async function () {
            clearFormError();
            const type = typeInput.value;
            const payload = {
                question_type: type,
                label: labelInput.value.trim(),
                help_text: isPageBreak(type) ? "" : helpInput.value.trim(),
                required: isPageBreak(type) ? false : requiredInput.checked,
                config: readConfigFromForm(type),
            };
            if (!isPageBreak(type) && !payload.label) {
                showFormError(labels.labelRequired);
                return;
            }
            if (type === TYPE_MAP_POINTS) {
                const cats = payload.config.categories || [];
                if (!cats.length || !cats[0].key || !cats[0].label) {
                    showFormError("Category key and label are required.");
                    return;
                }
                const pointChoices = payload.config.point_choices;
                if (pointChoices) {
                    const options = pointChoices.options || [];
                    if (options.length < 2) {
                        showFormError("At least two point detail options are required.");
                        return;
                    }
                }
            }
            if (isChoiceType(type)) {
                const options = payload.config.options || [];
                if (options.length < 2) {
                    showFormError("At least two options are required.");
                    return;
                }
            }
            try {
                let data;
                if (editingId) {
                    data = await apiJson(detailUrl(editingId), "PATCH", payload);
                } else {
                    data = await apiJson(createUrl, "POST", payload);
                }
                if (data.question) {
                    updateQuestionInDom(data.question);
                }
                if (modal) modal.hide();
            } catch (e) {
                if (e.data && e.data.errors) {
                    showFormError(formatErrors(e.data.errors));
                } else {
                    showFormError(e.message || labels.requestFailed);
                }
            }
        });
    }

    if (listEl && typeof Sortable !== "undefined") {
        Sortable.create(listEl, {
            animation: 150,
            handle: ".question-drag-handle",
            draggable: ".question-item",
            onEnd: async function () {
                const ids = [];
                listEl.querySelectorAll(".question-item").forEach(function (el) {
                    ids.push(parseInt(el.getAttribute("data-question-id"), 10));
                });
                try {
                    await apiJson(reorderUrl, "POST", { order: ids });
                    ids.forEach(function (id, index) {
                        if (questionsById[id]) {
                            questionsById[id].order = index;
                        }
                    });
                    refreshPageNumbers();
                } catch (e) {
                    window.alert(e.message || labels.reorderFailed);
                    window.location.reload();
                }
            },
        });
    }
})();
