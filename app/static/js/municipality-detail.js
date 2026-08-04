(function () {
    "use strict";

    function readJsonScript(id) {
        const el = document.getElementById(id);
        if (!el) return null;
        return JSON.parse(el.textContent);
    }

    function getColorForPM(value, colorSteps) {
        if (isNaN(value)) {
            return [128, 128, 128];
        }
        for (let i = 0; i < colorSteps.length - 1; i++) {
            if (value >= colorSteps[i][0] && value < colorSteps[i + 1][0]) {
                return colorSteps[i][1];
            }
        }
        return colorSteps[colorSteps.length - 1][1];
    }

    function getMean(arr) {
        let acc = 0;
        let count = 0;
        for (let i = 0; i < arr.length; i++) {
            if (isNaN(arr[i])) continue;
            acc += Number(arr[i]);
            count++;
        }
        return count === 0 ? NaN : acc / count;
    }

    function createLegend(colorSteps) {
        const legendDiv = document.getElementById("legend");
        if (!legendDiv) return;
        legendDiv.innerHTML = "";
        for (let i = 0; i < colorSteps.length; i++) {
            const from = colorSteps[i][0];
            const to = colorSteps[i + 1] ? colorSteps[i + 1][0] : "+";
            const rgb = colorSteps[i][1];
            const description = colorSteps[i][2];
            const colorString = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;

            const item = document.createElement("div");
            item.style.display = "flex";
            item.style.flexDirection = "row";
            item.style.alignItems = "center";
            item.style.marginBottom = "4px";

            const colorBox = document.createElement("span");
            colorBox.style.background = colorString;
            colorBox.style.width = "18px";
            colorBox.style.height = "18px";
            colorBox.style.display = "inline-block";
            colorBox.style.marginRight = "8px";
            colorBox.style.border = "1px solid #ccc";
            colorBox.style.borderRadius = "50%";

            const labelText = document.createElement("span");
            labelText.innerHTML = `${from}${to !== "+" ? "&ndash;" + to : "+"} µg/m³ | <strong>${description}</strong>`;
            labelText.style.fontSize = "0.8rem";

            item.appendChild(colorBox);
            item.appendChild(labelText);
            legendDiv.appendChild(item);
        }
    }

    function inBbox(lat, lon, bbox) {
        if (!bbox || bbox.length !== 4) return true;
        const [minx, miny, maxx, maxy] = bbox;
        return lon >= minx && lon <= maxx && lat >= miny && lat <= maxy;
    }

    function initMap(config) {
        const colorStepsArray = [colorStepsPM1, colorStepsPM25, colorStepsPM10];
        const centroid = config.centroid || [47.5, 13.3];
        const map = L.map("map").setView(centroid, 13);

        L.tileLayer(
            "https://mapsneu.wien.gv.at/basemap/bmapgrau/{type}/google3857/{z}/{y}/{x}.{format}",
            {
                maxZoom: 19,
                attribution: "Datenquelle: basemap.at",
                type: "normal",
                format: "png",
                bounds: [
                    [46.35877, 8.782379],
                    [49.037872, 17.189532],
                ],
            }
        ).addTo(map);

        if (config.bbox && config.bbox.length === 4) {
            const [minx, miny, maxx, maxy] = config.bbox;
            map.fitBounds([
                [miny, minx],
                [maxy, maxx],
            ]);
        }

        let stationData = [];
        let markerLayer = null;

        function addMarkerLayer(pmTypeIndex, colorSteps) {
            if (markerLayer != null) {
                map.removeLayer(markerLayer);
            }
            markerLayer = L.markerClusterGroup({
                iconCreateFunction: function (cluster) {
                    const meanPM = getMean(
                        cluster.getAllChildMarkers().map((marker) => marker.pm)
                    );
                    const rgb = getColorForPM(meanPM, colorSteps);
                    const colorString = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
                    const brightness =
                        (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000;
                    const textColor = brightness > 125 ? "black" : "white";
                    const displayValue = isNaN(meanPM) ? "" : meanPM.toFixed(1);

                    return L.divIcon({
                        iconSize: [40, 40],
                        className: "",
                        html: `<div class="clickable" style="height:3.5em;width:3.5em;background-color:${colorString};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10pt;border:1px solid white;"><span style="color:${textColor};">${displayValue}</span></div>`,
                    });
                },
                showCoverageOnHover: false,
            });

            const markerList = [];
            const pmKey = ["pm1", "pm25", "pm10"][pmTypeIndex];

            for (let i = 0; i < stationData.length; i++) {
                const station = stationData[i];
                if (!inBbox(station.lat, station.lon, config.bbox)) {
                    continue;
                }
                const pmValue = station[pmKey];
                const rgb = getColorForPM(pmValue, colorSteps);
                const colorString = `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
                const brightness =
                    (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000;
                const textColor = brightness > 125 ? "black" : "white";
                const displayValue = isNaN(pmValue) ? "" : pmValue.toFixed(1);

                const html = `<a class="hiddenlink clickable" href="/stations/${station.stationID}"><div style="height:3.5em;width:3.5em;background-color:${colorString};border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10pt;"><span style="color:${textColor};">${displayValue}</span></div></a>`;

                const marker = L.marker([station.lat, station.lon], {
                    icon: L.divIcon({
                        iconSize: [40, 40],
                        className: "",
                        html: html,
                    }),
                });
                marker.pm = pmValue;
                markerList.push(marker);
            }

            markerLayer.addLayers(markerList);
            map.addLayer(markerLayer);
        }

        function showPM(pmTypeIndex) {
            const colorSteps = colorStepsArray[pmTypeIndex];
            addMarkerLayer(pmTypeIndex, colorSteps);
            createLegend(colorSteps);
        }

        async function fetchMarkerData() {
            const response = await fetch(`${config.apiUrl}/station/current/all`);
            const text = await response.text();
            const items = text.split("\n");
            stationData = [];
            for (let row = 0; row < items.length; row++) {
                if (items[row].length === 0 || row === 0) continue;
                const data = items[row].split(",");
                const [stationID, lat, lon, pm1, pm25, pm10] = data;
                stationData.push({
                    stationID,
                    lat: parseFloat(lat),
                    lon: parseFloat(lon),
                    pm1: parseFloat(pm1),
                    pm25: parseFloat(pm25),
                    pm10: parseFloat(pm10),
                });
            }
        }

        const pmSelect = document.getElementById("pm-select");
        if (pmSelect) {
            pmSelect.addEventListener("change", function () {
                const idx = pmSelect.selectedIndex;
                showPM(idx);
            });
        }

        fetchMarkerData().then(() => {
            showPM(1);
        });
    }

    function initBarChart(canvasId, dataScriptId, labelSuffix) {
        const canvas = document.getElementById(canvasId);
        const data = readJsonScript(dataScriptId);
        if (!canvas || !data || typeof Chart === "undefined") return;

        const labels = Object.keys(data);
        const values = labels.map((key) => data[key]);

        new Chart(canvas, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: labelSuffix,
                        data: values,
                        backgroundColor: "rgba(54, 162, 235, 0.6)",
                        borderColor: "rgba(54, 162, 235, 1)",
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true },
                },
            },
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        const config = readJsonScript("municipality-map-config");
        if (config && typeof L !== "undefined") {
            initMap(config);
        }
        initBarChart("landuse-bars", "landuse-shares-data", "%");
        initBarChart("heat-landuse-bars", "heat-landuse-data", "°C");
    });
})();
