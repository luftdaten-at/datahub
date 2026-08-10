(function () {
    "use strict";

    let sharedMap = null;
    let boundaryLayer = null;
    const questionStates = {};
    let activeQuestionId = null;
    let visibleQuestionIds = [];
    let openPopupAfterRedraw = null;

    function readConfig() {
        const el = document.getElementById("survey-map-config");
        if (!el) return null;
        try {
            return JSON.parse(el.textContent);
        } catch {
            return null;
        }
    }

    function readUiLabels() {
        const el = document.getElementById("survey-form-ui");
        if (!el) {
            return {
                back: "Back",
                next: "Next",
                page: "Page %(current)s of %(total)s",
                maxPoints: "Maximum %(max)s points allowed.",
                activeQuestion: "Placing points for: %(label)s",
                noSelection: "No selection yet",
            };
        }
        return {
            back: el.dataset.labelBack || "Back",
            next: el.dataset.labelNext || "Next",
            page: el.dataset.labelPage || "Page %(current)s of %(total)s",
            maxPoints: el.dataset.labelMaxPoints || "Maximum %(max)s points allowed.",
            activeQuestion: el.dataset.labelActiveQuestion || "Placing points for: %(label)s",
            noSelection: el.dataset.labelNoSelection || "No selection yet",
        };
    }

    function formatLabel(template, replacements) {
        let text = template || "";
        Object.keys(replacements).forEach(function (key) {
            text = text.split("%(" + key + ")s").join(String(replacements[key]));
        });
        return text;
    }

    function addBasemapLayer(map) {
        return L.tileLayer(
            "https://mapsneu.wien.gv.at/basemap/bmapgrau/{type}/google3857/{z}/{y}/{x}.{format}",
            {
                maxZoom: 19,
                attribution: "Datenquelle: basemap.at",
                type: "normal",
                format: "png",
            }
        ).addTo(map);
    }

    function extractExteriorRings(geojson) {
        const rings = [];

        function addFromGeometry(geometry) {
            if (!geometry) return;
            if (geometry.type === "Polygon") {
                if (geometry.coordinates && geometry.coordinates[0]) {
                    rings.push(geometry.coordinates[0]);
                }
                return;
            }
            if (geometry.type === "MultiPolygon") {
                (geometry.coordinates || []).forEach(function (polygon) {
                    if (polygon && polygon[0]) {
                        rings.push(polygon[0]);
                    }
                });
                return;
            }
            if (geometry.type === "GeometryCollection") {
                (geometry.geometries || []).forEach(addFromGeometry);
            }
        }

        if (geojson.type === "FeatureCollection") {
            (geojson.features || []).forEach(function (feature) {
                addFromGeometry(feature.geometry);
            });
        } else if (geojson.type === "Feature") {
            addFromGeometry(geojson.geometry);
        } else {
            addFromGeometry(geojson);
        }

        return rings;
    }

    function reverseRing(ring) {
        return ring.slice().reverse();
    }

    function buildOutsideMaskGeoJSON(boundaryGeojson) {
        const worldRing = [
            [-180, -90],
            [180, -90],
            [180, 90],
            [-180, 90],
            [-180, -90],
        ];
        const holes = extractExteriorRings(boundaryGeojson).map(reverseRing);
        return {
            type: "Feature",
            geometry: {
                type: "Polygon",
                coordinates: [worldRing].concat(holes),
            },
        };
    }

    function loadBoundaryOnMap(map, boundaryUrl) {
        if (!boundaryUrl) return Promise.resolve(null);
        return fetch(boundaryUrl)
            .then(function (r) { return r.json(); })
            .then(function (geojson) {
                if (boundaryLayer) {
                    map.removeLayer(boundaryLayer);
                }

                boundaryLayer = L.layerGroup();

                L.geoJSON(buildOutsideMaskGeoJSON(geojson), {
                    style: {
                        fillColor: "#808080",
                        fillOpacity: 0.5,
                        stroke: false,
                    },
                }).addTo(boundaryLayer);

                const outlineLayer = L.geoJSON(geojson, {
                    style: {
                        color: "#3388ff",
                        weight: 2,
                        fillOpacity: 0,
                    },
                }).addTo(boundaryLayer);

                boundaryLayer.addTo(map);
                try {
                    map.fitBounds(outlineLayer.getBounds());
                } catch (e) { /* ignore */ }
                return boundaryLayer;
            })
            .catch(function () { return null; });
    }

    function getQuestionState(questionId) {
        if (!questionStates[questionId]) {
            questionStates[questionId] = {
                points: [],
                markers: [],
                markerLayer: null,
            };
        }
        return questionStates[questionId];
    }

    function syncHiddenInput(questionId) {
        const hiddenInput = document.getElementById("q_" + questionId);
        const state = getQuestionState(questionId);
        if (hiddenInput) {
            hiddenInput.value = JSON.stringify(state.points);
        }
    }

    function formatChoicesSummary(pt, labels) {
        const choices = pt.choices || [];
        if (!choices.length) {
            return labels.noSelection;
        }
        return choices.join(", ");
    }

    function buildPointChoicesPopupContent(pt, questionId, pointIndex, config) {
        const qConfig = (config.questions || {})[String(questionId)] || {};
        const pointChoices = qConfig.point_choices;
        if (!pointChoices || !pointChoices.options || !pointChoices.options.length) {
            return null;
        }

        const container = document.createElement("div");
        container.className = "survey-point-popup";

        if (pointChoices.help_text) {
            const help = document.createElement("p");
            help.className = "small text-muted mb-2";
            help.textContent = pointChoices.help_text;
            container.appendChild(help);
        }

        const selected = new Set(pt.choices || []);
        const inputName = "point-choices-" + questionId + "-" + pointIndex;
        const isMultiple = pointChoices.mode === "multiple";

        pointChoices.options.forEach(function (option, optionIndex) {
            const row = document.createElement("div");
            row.className = "form-check mb-1";

            const input = document.createElement("input");
            input.className = "form-check-input";
            input.type = isMultiple ? "checkbox" : "radio";
            input.name = inputName;
            input.id = inputName + "-" + optionIndex;
            input.value = option;
            input.checked = selected.has(option);

            const label = document.createElement("label");
            label.className = "form-check-label";
            label.setAttribute("for", input.id);
            label.textContent = option;

            input.addEventListener("change", function () {
                if (isMultiple) {
                    pt.choices = Array.prototype.slice.call(
                        container.querySelectorAll('input[type="checkbox"]:checked')
                    ).map(function (el) { return el.value; });
                } else {
                    pt.choices = input.checked ? [option] : [];
                }
                syncHiddenInput(questionId);
                renderPointsList(questionId, config);
            });

            row.appendChild(input);
            row.appendChild(label);
            container.appendChild(row);
        });

        return container;
    }

    function bindPointPopup(marker, pt, questionId, pointIndex, config) {
        const content = buildPointChoicesPopupContent(pt, questionId, pointIndex, config);
        if (!content) return;
        marker.bindPopup(content, { maxWidth: 280, autoClose: false, closeOnClick: false });
        marker.on("click", function () {
            marker.openPopup();
        });
    }

    function renderPointsList(questionId, config) {
        const listEl = document.getElementById("points-list-q-" + questionId);
        if (!listEl) return;
        const qConfig = (config.questions || {})[String(questionId)] || {};
        const categories = qConfig.categories || [];
        const hasPointChoices = !!(qConfig.point_choices && qConfig.point_choices.options &&
            qConfig.point_choices.options.length);
        const state = getQuestionState(questionId);
        const labels = readUiLabels();
        listEl.innerHTML = "";
        state.points.forEach(function (pt, idx) {
            const cat = categories.find(function (c) { return c.id === pt.category_id; });
            const row = document.createElement("div");
            row.className = "border rounded p-2 mb-2";
            let summaryHtml =
                "<strong>Point " + (idx + 1) + "</strong> (" +
                (cat ? cat.label : pt.category_id) + ") " +
                pt.lat.toFixed(5) + ", " + pt.lon.toFixed(5);
            if (hasPointChoices) {
                summaryHtml +=
                    '<div class="small text-muted mt-1">' +
                    formatChoicesSummary(pt, labels) +
                    "</div>";
            }
            row.innerHTML = summaryHtml;
            const commentInput = document.createElement("input");
            commentInput.type = "text";
            commentInput.className = "form-control form-control-sm mt-1";
            commentInput.placeholder = "Comment";
            commentInput.value = pt.comment || "";
            commentInput.addEventListener("input", function () {
                pt.comment = commentInput.value;
                syncHiddenInput(questionId);
            });
            const removeBtn = document.createElement("button");
            removeBtn.type = "button";
            removeBtn.className = "btn btn-sm btn-outline-danger mt-1";
            removeBtn.textContent = "Remove";
            removeBtn.addEventListener("click", function () {
                if (sharedMap && state.markers[idx]) {
                    sharedMap.removeLayer(state.markers[idx]);
                }
                state.markers.splice(idx, 1);
                state.points.splice(idx, 1);
                syncHiddenInput(questionId);
                renderPointsList(questionId, config);
                redrawAllMarkers(config, visibleQuestionIds);
            });
            row.appendChild(commentInput);
            row.appendChild(removeBtn);
            listEl.appendChild(row);
        });
    }

    function populateActiveQuestionSelect(config, questionIds) {
        const select = document.getElementById("survey-active-map-question");
        if (!select) return;
        select.innerHTML = "";
        (questionIds || []).forEach(function (questionId) {
            const qConfig = (config.questions || {})[String(questionId)] || {};
            const opt = document.createElement("option");
            opt.value = questionId;
            opt.textContent = qConfig.label || ("Question " + questionId);
            select.appendChild(opt);
        });
    }

    function redrawAllMarkers(config, questionIds) {
        if (!sharedMap) return;
        Object.keys(questionStates).forEach(function (questionId) {
            const state = getQuestionState(questionId);
            state.markers.forEach(function (marker) {
                sharedMap.removeLayer(marker);
            });
            state.markers = [];
        });

        const visibleIds = (questionIds || []).map(String);
        visibleIds.forEach(function (questionId) {
            const qConfig = (config.questions || {})[questionId] || {};
            const categories = qConfig.categories || [];
            const state = getQuestionState(questionId);
            const isActive = questionId === String(activeQuestionId);
            state.points.forEach(function (pt, pointIndex) {
                const cat = categories.find(function (c) { return c.id === pt.category_id; });
                const color = cat ? cat.color : "#3388ff";
                const marker = L.circleMarker([pt.lat, pt.lon], {
                    radius: isActive ? 9 : 7,
                    color: color,
                    fillColor: color,
                    fillOpacity: isActive ? 0.85 : 0.45,
                    weight: isActive ? 2 : 1,
                }).addTo(sharedMap);
                bindPointPopup(marker, pt, questionId, pointIndex, config);
                state.markers.push(marker);
            });
        });

        if (openPopupAfterRedraw) {
            const target = openPopupAfterRedraw;
            openPopupAfterRedraw = null;
            const state = getQuestionState(target.questionId);
            const marker = state.markers[target.pointIndex];
            if (marker) {
                marker.openPopup();
            }
        }
    }

    function getMapQuestionsOnPage(pageEl) {
        if (!pageEl) return [];
        return Array.prototype.slice.call(
            pageEl.querySelectorAll('.survey-question[data-question-type="map_points"]')
        ).map(function (el) {
            return el.getAttribute("data-question-id");
        });
    }

    function updateMapModeForPage(pageEl, config, labels) {
        const activeSelect = document.getElementById("survey-active-map-question");
        const mapQuestions = getMapQuestionsOnPage(pageEl);
        visibleQuestionIds = mapQuestions;

        if (!mapQuestions.length) {
            activeQuestionId = null;
            if (activeSelect) activeSelect.classList.add("d-none");
            if (sharedMap) {
                sharedMap.off("click");
            }
            redrawAllMarkers(config, []);
            return;
        }

        if (!activeQuestionId || mapQuestions.indexOf(String(activeQuestionId)) === -1) {
            activeQuestionId = mapQuestions[0];
        }

        if (activeSelect) {
            populateActiveQuestionSelect(config, mapQuestions);
            activeSelect.classList.remove("d-none");
            activeSelect.value = String(activeQuestionId);
        }

        if (sharedMap) {
            sharedMap.off("click");
            sharedMap.on("click", function (e) {
                handleMapClick(activeQuestionId, e, config, labels);
            });
        }
        redrawAllMarkers(config, mapQuestions);
    }

    function handleMapClick(questionId, e, config, labels) {
        const qConfig = (config.questions || {})[String(questionId)] || {};
        const maxPoints = qConfig.max_points || 50;
        const categories = qConfig.categories || [];
        const pointChoices = qConfig.point_choices;
        const state = getQuestionState(questionId);
        if (state.points.length >= maxPoints) {
            alert(formatLabel(labels.maxPoints, { max: maxPoints }));
            return;
        }
        const categoryId = categories.length ? categories[0].id : null;
        state.points.push({
            lat: e.latlng.lat,
            lon: e.latlng.lng,
            category_id: categoryId,
            comment: "",
            choices: [],
        });
        syncHiddenInput(questionId);
        renderPointsList(questionId, config);
        if (pointChoices && pointChoices.options && pointChoices.options.length) {
            openPopupAfterRedraw = {
                questionId: String(questionId),
                pointIndex: state.points.length - 1,
            };
        }
        redrawAllMarkers(config, visibleQuestionIds);
    }

    function initSharedMap(config, labels) {
        const overviewEl = document.getElementById("survey-boundary-overview");
        if (!overviewEl || !config || !config.boundaryUrl || typeof L === "undefined") {
            return;
        }

        sharedMap = L.map(overviewEl, {
            zoomControl: true,
            scrollWheelZoom: true,
            dragging: true,
        }).setView([47.5, 13.3], 12);
        addBasemapLayer(sharedMap);
        loadBoundaryOnMap(sharedMap, config.boundaryUrl).then(function () {
            setTimeout(function () {
                if (sharedMap) sharedMap.invalidateSize();
            }, 100);
        });

        populateActiveQuestionSelect(config, []);
        Object.keys(config.questions || {}).forEach(function (questionId) {
            syncHiddenInput(questionId);
        });

        const activeSelect = document.getElementById("survey-active-map-question");
        if (activeSelect) {
            activeSelect.addEventListener("change", function () {
                activeQuestionId = activeSelect.value;
                const pages = document.querySelectorAll(".survey-page");
                const visiblePage = Array.prototype.slice.call(pages).find(function (p) {
                    return !p.classList.contains("d-none");
                });
                updateMapModeForPage(visiblePage, config, labels);
            });
        }

        window.addEventListener("resize", function () {
            if (sharedMap) sharedMap.invalidateSize();
        });
    }

    function initPageWizard(config, labels) {
        const pages = Array.prototype.slice.call(document.querySelectorAll(".survey-page"));
        if (!pages.length) return function () {};

        const backBtn = document.getElementById("survey-page-back");
        const nextBtn = document.getElementById("survey-page-next");
        const submitBtn = document.getElementById("survey-page-submit");
        const indicator = document.getElementById("survey-page-indicator");
        let currentIndex = 0;

        function formatPageLabel(current, total) {
            return labels.page
                .replace("%(current)s", String(current))
                .replace("%(total)s", String(total));
        }

        function validateCurrentPage() {
            const page = pages[currentIndex];
            const fields = page.querySelectorAll("input, select, textarea");
            for (let i = 0; i < fields.length; i++) {
                const field = fields[i];
                if (field.type === "hidden" || field.offsetParent === null) continue;
                if (!field.checkValidity()) {
                    field.reportValidity();
                    return false;
                }
            }
            return true;
        }

        function updateNav() {
            const total = pages.length;
            const isFirst = currentIndex === 0;
            const isLast = currentIndex === total - 1;

            pages.forEach(function (page, index) {
                page.classList.toggle("d-none", index !== currentIndex);
            });

            if (backBtn) backBtn.classList.toggle("d-none", isFirst);
            if (nextBtn) nextBtn.classList.toggle("d-none", isLast);
            if (submitBtn) submitBtn.classList.toggle("d-none", !isLast);
            if (indicator) {
                indicator.textContent = formatPageLabel(currentIndex + 1, total);
            }

            updateMapModeForPage(pages[currentIndex], config, labels);
            setTimeout(function () {
                if (sharedMap) sharedMap.invalidateSize();
            }, 50);
        }

        if (backBtn) {
            backBtn.addEventListener("click", function () {
                if (currentIndex > 0) {
                    currentIndex -= 1;
                    updateNav();
                }
            });
        }

        if (nextBtn) {
            nextBtn.addEventListener("click", function () {
                if (!validateCurrentPage()) return;
                if (currentIndex < pages.length - 1) {
                    currentIndex += 1;
                    updateNav();
                }
            });
        }

        updateNav();
        return updateNav;
    }

    document.addEventListener("DOMContentLoaded", function () {
        const config = readConfig();
        const labels = readUiLabels();
        initSharedMap(config, labels);
        initPageWizard(config, labels);
    });
})();
