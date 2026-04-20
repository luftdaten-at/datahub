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
            return;
        }
        if (!options || !options.tableSelector || !options.filters || !options.filters.length) {
            console.warn("initBootstrapTableFilterToolbars: missing options");
            return;
        }
        var $table = $(options.tableSelector);
        if (!$table.length) {
            return;
        }

        var filters = options.filters.map(function (f) {
            return {
                rowDataKey: f.rowDataKey,
                filterField: f.filterField,
                toolbarSelector: f.toolbarSelector,
                buttonHostSelector: f.buttonHostSelector,
                sort: f.sort || "locale",
                $toolbar: $(f.toolbarSelector),
                $btnHost: $(f.buttonHostSelector),
            };
        });

        for (var i = 0; i < filters.length; i++) {
            var fi = filters[i];
            if (!fi.$toolbar.length || !fi.$btnHost.length) {
                return;
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
                    seen[raw] = true;
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

        function applyCombinedFilter() {
            try {
                var spec = {};
                for (var j = 0; j < filters.length; j++) {
                    if (active[j] !== "__all__") {
                        spec[filters[j].filterField] = [active[j]];
                    }
                }
                $table.bootstrapTable("filterBy", spec);
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
                if (active[i] !== "__all__" && !Object.prototype.hasOwnProperty.call(keySet, active[i])) {
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

        $(function () {
            initWhenReady();
        });
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

    global.LuftdatenDatahub = global.LuftdatenDatahub || {};
    global.LuftdatenDatahub.initBootstrapTableFilterToolbars = initBootstrapTableFilterToolbars;
    global.LuftdatenDatahub.initBootstrapTableFirmwareFilter = initBootstrapTableFirmwareFilter;
    global.LuftdatenDatahub.compareFirmwareOrder = compareFirmwareOrder;
})(typeof window !== "undefined" ? window : this);
