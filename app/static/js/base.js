// static/js/base.js
(function (global) {
    "use strict";

    function segmentIsAllDigits(s) {
        return s !== "" && /^[0-9]+$/.test(s);
    }

    /** Dot-separated numeric order (1.5.5 before 1.5.14). Empty last. */
    function compareFirmwareOrder(a, b) {
        if (a === "" && b === "") {
            return 0;
        }
        if (a === "") {
            return 1;
        }
        if (b === "") {
            return -1;
        }
        var partsA = a.split(".");
        var partsB = b.split(".");
        var n = Math.max(partsA.length, partsB.length);
        for (var i = 0; i < n; i++) {
            var sa = partsA[i] || "";
            var sb = partsB[i] || "";
            var aNum = segmentIsAllDigits(sa);
            var bNum = segmentIsAllDigits(sb);
            if (aNum && bNum) {
                var na = parseInt(sa, 10);
                var nb = parseInt(sb, 10);
                if (na !== nb) {
                    return na - nb;
                }
            } else {
                var c = sa.localeCompare(sb, undefined, {
                    sensitivity: "base",
                    numeric: true,
                });
                if (c !== 0) {
                    return c;
                }
            }
        }
        return 0;
    }

    function compareLocaleEmptyLast(a, b) {
        if (a === "" && b === "") {
            return 0;
        }
        if (a === "") {
            return 1;
        }
        if (b === "") {
            return -1;
        }
        return a.localeCompare(b, undefined, { sensitivity: "base", numeric: true });
    }

    /**
     * One or more Bootstrap Table chip toolbars (filterBy + hidden columns).
     * Chip options follow the current page (pagination + page size) and other
     * row visibility changes via post-body.bs.table.
     *
     * @param {Object} options
     * @param {string} options.tableSelector
     * @param {Array<Object>} options.filters
     * @param {string} options.filters[].rowDataKey - data-* on tr (informational / HTML)
     * @param {string} options.filters[].filterField - data-field; used with getData() for chip values
     * @param {string} options.filters[].toolbarSelector
     * @param {string} options.filters[].buttonHostSelector
     * @param {('semver'|'locale')} [options.filters[].sort='locale']
     */
    function initBootstrapTableFilterToolbars(options) {
        var $ = global.jQuery || global.$;
        if (!$) {
            console.warn("initBootstrapTableFilterToolbars: jQuery not found");
            return null;
        }
        if (!options || !options.tableSelector || !options.filters || !options.filters.length) {
            console.warn("initBootstrapTableFilterToolbars: missing options");
            return null;
        }
        var $table = $(options.tableSelector);
        if (!$table.length) {
            return null;
        }

        var filters = options.filters.map(function (f) {
            return {
                rowDataKey: f.rowDataKey,
                filterField: f.filterField,
                toolbarSelector: f.toolbarSelector,
                buttonHostSelector: f.buttonHostSelector,
                sort: f.sort || "locale",
                match: f.match || "exact",
                $toolbar: $(f.toolbarSelector),
                $btnHost: $(f.buttonHostSelector),
            };
        });

        for (var i = 0; i < filters.length; i++) {
            var fi = filters[i];
            if (!fi.$toolbar.length || !fi.$btnHost.length) {
                return null;
            }
        }

        var active = filters.map(function () {
            return "__all__";
        });

        var builtStates = [];

        function collectValues(fi) {
            var seen = {};
            try {
                var rows = $table.bootstrapTable("getData", { useCurrentPage: true });
                if (!rows || !rows.length) {
                    return [];
                }
                rows.forEach(function (row) {
                    var v = row[fi.filterField];
                    var raw = String(v == null ? "" : v);
                    if (fi.match === "tokenComma") {
                        if (raw === "") {
                            seen[""] = true;
                        } else {
                            raw.split(", ").forEach(function (token) {
                                if (token) {
                                    seen[token] = true;
                                }
                            });
                        }
                    } else {
                        seen[raw] = true;
                    }
                });
            } catch (e) {
                console.warn("collectValues getData:", e);
            }
            var keys = Object.keys(seen);
            if (fi.sort === "semver") {
                keys.sort(compareFirmwareOrder);
            } else {
                keys.sort(compareLocaleEmptyLast);
            }
            return keys;
        }

        function rowMatchesActiveFilters(row) {
            for (var j = 0; j < filters.length; j++) {
                if (active[j] === "__all__") {
                    continue;
                }
                var fi = filters[j];
                var cell = String(row[fi.filterField] == null ? "" : row[fi.filterField]);
                if (fi.match === "tokenComma") {
                    if (active[j] === "") {
                        if (cell !== "") {
                            return false;
                        }
                    } else if (cell.split(", ").indexOf(active[j]) === -1) {
                        return false;
                    }
                } else if (cell !== active[j]) {
                    return false;
                }
            }
            return true;
        }

        function applyCombinedFilter() {
            try {
                var hasActive = false;
                for (var j = 0; j < active.length; j++) {
                    if (active[j] !== "__all__") {
                        hasActive = true;
                        break;
                    }
                }
                if (!hasActive) {
                    $table.bootstrapTable("filterBy", {});
                    return;
                }
                var usesCustom = false;
                for (var k = 0; k < filters.length; k++) {
                    if (filters[k].match === "tokenComma") {
                        usesCustom = true;
                        break;
                    }
                }
                if (usesCustom || filters.length > 1) {
                    $table.bootstrapTable("filterBy", {}, {
                        filterAlgorithm: function (row) {
                            return rowMatchesActiveFilters(row);
                        },
                    });
                } else {
                    var spec = {};
                    if (active[0] !== "__all__") {
                        spec[filters[0].filterField] = [active[0]];
                    }
                    $table.bootstrapTable("filterBy", spec);
                }
            } catch (e) {
                console.warn("bootstrapTable filterBy:", e);
            }
        }

        function applyActiveHighlights() {
            for (var i = 0; i < filters.length; i++) {
                var fi = filters[i];
                var state = builtStates[i];
                if (!state) {
                    continue;
                }
                fi.$btnHost.find("button.bt-filter-chip").removeClass("active").attr("aria-pressed", "false");
                var key = active[i];
                var $btn = key === "__all__" ? state.$all : state.byRaw[key];
                if (!$btn || !$btn.length) {
                    active[i] = "__all__";
                    state.$all.addClass("active").attr("aria-pressed", "true");
                } else {
                    $btn.addClass("active").attr("aria-pressed", "true");
                }
            }
        }

        function buildGroup(index) {
            var fi = filters[index];
            var labelAll = fi.$toolbar.data("label-all") || "All";
            var labelNA = fi.$toolbar.data("label-na") || "N/A";

            function setActiveInGroup($btn) {
                fi.$btnHost.find("button.bt-filter-chip").removeClass("active").attr("aria-pressed", "false");
                $btn.addClass("active").attr("aria-pressed", "true");
            }

            fi.$btnHost.empty();

            var byRaw = {};

            var $all = $("<button>")
                .attr("type", "button")
                .addClass("btn btn-sm btn-outline-secondary bt-filter-chip")
                .attr("aria-pressed", "false")
                .text(labelAll)
                .on("click", function () {
                    setActiveInGroup($all);
                    active[index] = "__all__";
                    applyCombinedFilter();
                });
            fi.$btnHost.append($all);

            collectValues(fi).forEach(function (raw) {
                var display = raw === "" ? labelNA : raw;
                var $b = $("<button>")
                    .attr("type", "button")
                    .addClass("btn btn-sm btn-outline-primary bt-filter-chip")
                    .attr("aria-pressed", "false")
                    .text(display)
                    .on("click", function () {
                        setActiveInGroup($b);
                        active[index] = raw;
                        applyCombinedFilter();
                    });
                byRaw[raw] = $b;
                fi.$btnHost.append($b);
            });

            return { $all: $all, byRaw: byRaw };
        }

        function buildAllToolbars() {
            builtStates = [];
            for (var k = 0; k < filters.length; k++) {
                builtStates.push(buildGroup(k));
            }
            applyActiveHighlights();
        }

        function syncChipsToCurrentView() {
            if (!$table.data("bootstrap.table")) {
                return;
            }
            var dirty = false;
            for (var i = 0; i < filters.length; i++) {
                var fi = filters[i];
                var keys = collectValues(fi);
                var keySet = {};
                keys.forEach(function (k) {
                    keySet[k] = true;
                });
                if (
                    active[i] !== "__all__" &&
                    !Object.prototype.hasOwnProperty.call(keySet, active[i])
                ) {
                    active[i] = "__all__";
                    dirty = true;
                }
            }
            buildAllToolbars();
            if (dirty) {
                applyCombinedFilter();
            }
        }

        function initWhenReady() {
            if (!$table.data("bootstrap.table")) {
                setTimeout(initWhenReady, 50);
                return;
            }
            if (!$table.data("luftdatenFilterToolbarsBound")) {
                $table.data("luftdatenFilterToolbarsBound", true);
                $table.on("post-body.bs.table", syncChipsToCurrentView);
            }
            syncChipsToCurrentView();
        }

        function setFilter(index, raw) {
            if (index < 0 || index >= filters.length) {
                return;
            }
            if (!builtStates.length) {
                buildAllToolbars();
            }
            active[index] = raw;
            applyActiveHighlights();
            applyCombinedFilter();
        }

        function clearFilter(index) {
            setFilter(index, "__all__");
        }

        var api = {
            setFilter: setFilter,
            clearFilter: clearFilter,
        };
        $table.data("luftdatenFilterToolbars", api);

        $(function () {
            initWhenReady();
        });

        return api;
    }

    /** @deprecated Prefer initBootstrapTableFilterToolbars with a filters array */
    function initBootstrapTableFirmwareFilter(options) {
        if (!options || !options.tableSelector) {
            return;
        }
        initBootstrapTableFilterToolbars({
            tableSelector: options.tableSelector,
            filters: [
                {
                    rowDataKey: "firmware",
                    filterField: options.filterField || "firmware_filter",
                    toolbarSelector: options.toolbarSelector,
                    buttonHostSelector: options.buttonHostSelector,
                    sort: "semver",
                },
            ],
        });
    }

    function initMapLegendCollapses() {
        document.querySelectorAll(".map-legend-collapse").forEach(function (collapseEl) {
            if (!collapseEl.id) {
                return;
            }
            var toggle = document.querySelector(
                '.map-legend-toggle[data-bs-target="#' + collapseEl.id + '"]'
            );
            if (!toggle) {
                return;
            }
            var icon = toggle.querySelector(".map-legend-toggle-icon");
            if (!icon) {
                return;
            }
            collapseEl.addEventListener("shown.bs.collapse", function () {
                icon.classList.remove("bi-chevron-down");
                icon.classList.add("bi-chevron-up");
            });
            collapseEl.addEventListener("hidden.bs.collapse", function () {
                icon.classList.remove("bi-chevron-up");
                icon.classList.add("bi-chevron-down");
            });
        });
    }

    global.LuftdatenDatahub = global.LuftdatenDatahub || {};
    global.LuftdatenDatahub.initBootstrapTableFilterToolbars = initBootstrapTableFilterToolbars;
    global.LuftdatenDatahub.initBootstrapTableFirmwareFilter = initBootstrapTableFirmwareFilter;
    global.LuftdatenDatahub.compareFirmwareOrder = compareFirmwareOrder;
    global.LuftdatenDatahub.initMapLegendCollapses = initMapLegendCollapses;

    if (typeof document !== "undefined") {
        document.addEventListener("DOMContentLoaded", initMapLegendCollapses);
    }
})(typeof window !== "undefined" ? window : this);
