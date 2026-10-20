/**
 * RoadGuard AI - Pune Municipal Corporation Dashboard Script
 * Handles real-time hardware telemetry monitoring, Leaflet map rendering,
 * browser geolocation ("Locate Me"), mode switching, and workflow transitions.
 */

let map = null;
let markersLayer = null;
let userLocationLayer = null;
let activeHotspots = [];
let pollingInterval = null;
let devicePollingInterval = null;
let currentMode = "HARDWARE"; // Default to real hardware view

document.addEventListener("DOMContentLoaded", () => {
    initMap();
    initEventListeners();
    fetchModelStatus();
    fetchDeviceStatus();
    refreshDashboard();

    // Fast polling for device connection heartbeat (every 2s)
    devicePollingInterval = setInterval(fetchDeviceStatus, 2000);

    // Main polling for hotspots and KPI metrics (every 3s)
    pollingInterval = setInterval(refreshDashboard, 3000);
});

/**
 * Initializes Leaflet interactive map centered on Pune City
 */
function initMap() {
    // Pune coordinates: 18.5204 N, 73.8567 E
    map = L.map("map", {
        center: [18.5204, 73.8567],
        zoom: 12.5,
        zoomControl: true
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> &copy; <a href="https://carto.com/">CARTO</a>',
        subdomains: "abcd",
        maxZoom: 19
    }).addTo(map);

    markersLayer = L.layerGroup().addTo(map);
    userLocationLayer = L.layerGroup().addTo(map);
}

/**
 * Attaches UI buttons, filter listeners, and Locate Me handler
 */
function initEventListeners() {
    // Mode Switcher (Hardware vs Simulation vs All)
    const modeSelect = document.getElementById("systemModeSelect");
    if (modeSelect) {
        modeSelect.addEventListener("change", (e) => {
            currentMode = e.target.value;
            const badge = document.getElementById("activeModeBadge");
            if (currentMode === "HARDWARE") {
                badge.innerHTML = '<i class="fa-solid fa-microchip"></i> Showing: Real Hardware Telemetry';
                badge.style.color = "#34D399";
                badge.style.borderColor = "rgba(52, 211, 153, 0.4)";
            } else if (currentMode === "SIMULATION") {
                badge.innerHTML = '<i class="fa-solid fa-flask"></i> Showing: Synthetic Simulation Demo';
                badge.style.color = "#FBBF24";
                badge.style.borderColor = "rgba(251, 191, 36, 0.4)";
            } else {
                badge.innerHTML = '<i class="fa-solid fa-layer-group"></i> Showing: All Data Sources';
                badge.style.color = "#38BDF8";
                badge.style.borderColor = "rgba(56, 189, 248, 0.3)";
            }
            refreshDashboard();
        });
    }

    // Hazard Type Filter
    const typeFilter = document.getElementById("typeFilter");
    if (typeFilter) {
        typeFilter.addEventListener("change", () => {
            renderMarkers();
            renderHotspotsTable();
        });
    }

    // Repair Status Filter
    const statusFilter = document.getElementById("statusFilter");
    if (statusFilter) {
        statusFilter.addEventListener("change", () => {
            renderMarkers();
            renderHotspotsTable();
        });
    }

    // Locate Me (Browser Geolocation)
    const btnLocate = document.getElementById("btnLocateMe");
    if (btnLocate) {
        btnLocate.addEventListener("click", handleBrowserLocateMe);
    }

    // Simulation Trigger
    document.getElementById("btnRunSim").addEventListener("click", () => {
        triggerLiveSimulation();
    });

    // Seed Hotspots
    document.getElementById("btnSeedDemo").addEventListener("click", () => {
        seedPuneDemoHotspots();
    });
}

/**
 * Handles Browser Geolocation for map centering (strictly separate from hardware GPS)
 */
function handleBrowserLocateMe() {
    if (!navigator.geolocation) {
        alert("Browser geolocation is not supported by your browser.");
        return;
    }

    const btn = document.getElementById("btnLocateMe");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Locating...';

    navigator.geolocation.getCurrentPosition(
        (position) => {
            const userLat = position.coords.latitude;
            const userLon = position.coords.longitude;
            const accuracy = position.coords.accuracy;

            userLocationLayer.clearLayers();

            // Pulsing blue marker
            const userIcon = L.divIcon({
                className: "user-location-icon",
                html: '<div class="user-location-marker"></div>',
                iconSize: [18, 18],
                iconAnchor: [9, 9]
            });

            const marker = L.marker([userLat, userLon], { icon: userIcon });
            marker.bindPopup(`
                <div style="font-family:Inter,sans-serif; font-size:12px;">
                    <strong>Your Browser Location</strong><br>
                    📍 ${userLat.toFixed(5)}, ${userLon.toFixed(5)}<br>
                    <span style="color:#64748B; font-size:11px;">Accuracy: ±${Math.round(accuracy)}m</span><br>
                    <em style="color:#0284C7; font-size:10px;">(Used for map navigation only)</em>
                </div>
            `);
            userLocationLayer.addLayer(marker);

            // Accuracy circle
            const circle = L.circle([userLat, userLon], {
                radius: Math.max(accuracy, 25),
                color: "#3B82F6",
                fillColor: "#3B82F6",
                fillOpacity: 0.15,
                weight: 1
            });
            userLocationLayer.addLayer(circle);

            map.flyTo([userLat, userLon], 14, { duration: 1.2 });
            marker.openPopup();

            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-crosshairs"></i> Located';
            setTimeout(() => {
                btn.innerHTML = '<i class="fa-solid fa-crosshairs"></i> Locate Me';
            }, 3000);
        },
        (error) => {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-crosshairs"></i> Locate Me';
            let msg = "Could not obtain browser location.";
            if (error.code === error.PERMISSION_DENIED) {
                msg = "Location permission was denied. To use 'Locate Me', allow location access in your browser settings.";
            } else if (error.code === error.POSITION_UNAVAILABLE) {
                msg = "Location information is currently unavailable.";
            } else if (error.code === error.TIMEOUT) {
                msg = "Location request timed out.";
            }
            alert(msg);
        },
        { enableHighAccuracy: true, timeout: 8000, maximumAge: 10000 }
    );
}

/**
 * Queries connected hardware devices and updates connection / GPS strip
 */
async function fetchDeviceStatus() {
    try {
        const res = await fetch("/api/device-status");
        if (res.ok) {
            const data = await res.json();
            const devices = data.devices || [];

            const devDot = document.getElementById("hwDeviceDot");
            const devText = document.getElementById("hwDeviceText");
            const gpsText = document.getElementById("hwGpsText");

            if (devices.length > 0) {
                const latest = devices[0];
                if (latest.status === "ONLINE") {
                    devDot.className = "hw-indicator dot-online";
                    devText.textContent = `${latest.device_id} (Online • ${latest.ip_address || "LAN"} • seen ${latest.seconds_since_seen}s ago)`;
                    
                    if (latest.gps_fix) {
                        gpsText.innerHTML = `<span style="color:#10B981;">3D Fix (${latest.satellites} Sats • HDOP ${latest.hdop})</span>`;
                    } else {
                        gpsText.innerHTML = `<span style="color:#F59E0B;">Acquiring Satellites (${latest.satellites} Sats)</span>`;
                    }
                } else {
                    devDot.className = "hw-indicator dot-offline";
                    devText.textContent = `${latest.device_id} (Offline • last seen ${latest.seconds_since_seen}s ago)`;
                    gpsText.innerHTML = '<span style="color:#94A3B8;">GPS Inactive</span>';
                }
            } else {
                devDot.className = "hw-indicator dot-offline";
                devText.textContent = "No ESP32 connected (Waiting for /api/telemetry)";
                gpsText.innerHTML = '<span style="color:#94A3B8;">GPS Inactive</span>';
            }
        }
    } catch (e) {
        document.getElementById("hwDeviceText").textContent = "Backend Connection Error";
    }
}

/**
 * Queries active ML model status
 */
async function fetchModelStatus() {
    try {
        const res = await fetch("/api/model-status");
        if (res.ok) {
            const data = await res.json();
            const modelText = document.getElementById("hwModelText");
            if (data.readiness === "MODEL_READY") {
                modelText.innerHTML = `<span style="color:#10B981;">Random Forest (${data.classes.length} Classes, Ready)</span>`;
            } else {
                modelText.innerHTML = `<span style="color:#EF4444;">Model Not Ready (Training Required)</span>`;
            }
        }
    } catch (e) {
        document.getElementById("hwModelText").textContent = "Status Unknown";
    }
}

/**
 * Main polling function: fetches KPIs, Hotspots, and refreshes UI
 */
async function refreshDashboard() {
    try {
        // 1. Fetch Stats for current mode
        const statsRes = await fetch(`/api/stats?mode=${currentMode}`);
        if (statsRes.ok) {
            const stats = await statsRes.json();
            document.getElementById("kpiOpenReports").textContent = stats.open_reports ?? 0;
            document.getElementById("kpiHighPriority").textContent = stats.high_priority ?? 0;
            document.getElementById("kpiMediumPriority").textContent = stats.medium_priority ?? 0;
            document.getElementById("kpiResolved").textContent = stats.resolved ?? 0;
            document.getElementById("kpiActiveBuses").textContent = stats.active_buses ?? 1;
        }

        // 2. Fetch Hotspots for current mode
        const hotspotsRes = await fetch(`/api/hotspots?mode=${currentMode}`);
        if (hotspotsRes.ok) {
            const data = await hotspotsRes.json();
            activeHotspots = data.hotspots || [];
            renderMarkers();
            renderHotspotsTable();
            renderAlertsStream();
        }
    } catch (err) {
        console.warn("Polling update error:", err);
    }
}

/**
 * Creates custom colored pin icons with mode badge
 */
function getMarkerIcon(hazardType, priorityLevel, status, mode) {
    let color = "#0284C7"; // Default rough road blue
    let letter = "R";

    if (status === "VERIFIED") {
        color = "#10B981"; // Resolved emerald
        letter = "✓";
    } else if (hazardType === "POTHOLE") {
        color = "#EF4444"; // Pothole red
        letter = "P";
    } else if (hazardType === "SPEED_BREAKER") {
        color = "#F59E0B"; // Speed breaker amber
        letter = "B";
    } else if (hazardType === "UNKNOWN" || hazardType === "UNCERTAIN") {
        color = "#A855F7"; // Purple for unknown/review
        letter = "?";
    }

    const isHigh = (priorityLevel === "HIGH" && status !== "VERIFIED");
    const pulseHtml = isHigh ? '<div class="marker-pulse"></div>' : '';
    const modeBadge = (mode === "HARDWARE") ? "HW" : "SIM";

    return L.divIcon({
        className: "custom-hazard-marker",
        html: `
            <div style="position:relative; width:30px; height:30px;">
                ${pulseHtml}
                <div style="
                    width: 26px; height: 26px; border-radius: 50%;
                    background: ${color}; border: 2px solid #FFFFFF;
                    box-shadow: 0 2px 6px rgba(0,0,0,0.45);
                    display: flex; align-items: center; justify-content: center;
                    color: white; font-size: 11px; font-weight: bold;
                ">
                    ${letter}
                </div>
                <div style="
                    position: absolute; bottom: -2px; right: -4px;
                    background: #0F172A; border: 1px solid ${color};
                    border-radius: 3px; font-size: 8px; font-weight: 800;
                    color: #FFFFFF; padding: 0 2px; line-height: 10px;
                ">${modeBadge}</div>
            </div>
        `,
        iconSize: [30, 30],
        iconAnchor: [15, 15]
    });
}

/**
 * Renders all markers on the Leaflet map based on active filters
 */
function renderMarkers() {
    if (!markersLayer) return;
    markersLayer.clearLayers();

    const statusFilter = document.getElementById("statusFilter")?.value || "ALL";
    const typeFilter = document.getElementById("typeFilter")?.value || "ALL";

    activeHotspots.forEach(h => {
        if (statusFilter !== "ALL" && h.status !== statusFilter) return;
        if (typeFilter !== "ALL" && h.hazard_type !== typeFilter) return;

        const icon = getMarkerIcon(h.hazard_type, h.priority_level, h.status, h.mode);
        const marker = L.marker([h.latitude, h.longitude], { icon: icon });

        const isHw = (h.mode === "HARDWARE");
        const originTag = isHw
            ? '<span style="background:rgba(16,185,129,0.2); color:#10B981; padding:2px 6px; border-radius:3px; font-weight:700; font-size:10px;">REAL HARDWARE</span>'
            : '<span style="background:rgba(245,158,11,0.2); color:#F59E0B; padding:2px 6px; border-radius:3px; font-weight:700; font-size:10px;">SIMULATED DATA</span>';

        const popupContent = `
            <div style="min-width: 220px; font-family: Inter, sans-serif;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                    <span style="font-weight: 700; font-size: 14px; color: #0F172A;">${h.location_name || "Road Hazard"}</span>
                    ${originTag}
                </div>
                <div style="font-size: 11px; color: #475569; margin-bottom: 8px;">
                    📍 ${h.latitude.toFixed(5)}, ${h.longitude.toFixed(5)}
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px; font-size: 11px; margin-bottom: 8px;">
                    <div><strong>Hazard:</strong> ${h.hazard_type}</div>
                    <div><strong>Priority:</strong> <span style="font-weight:bold; color:${h.priority_level==='HIGH'?'#DC2626':'#D97706'}">${h.priority_level} (${h.priority_score})</span></div>
                    <div><strong>Passes:</strong> ${h.distinct_rides} (${h.observation_count} hits)</div>
                    <div><strong>Avg Conf:</strong> ${(h.avg_confidence*100).toFixed(0)}%</div>
                </div>
                <div style="font-size: 11px; margin-bottom: 8px;">
                    <strong>Status:</strong> <span class="status-tag status-${h.status.toLowerCase()}">${h.status}</span>
                </div>
                <button onclick="openStatusModal(${h.id}, '${h.location_name || h.hazard_type}', '${h.status}')"
                        style="width: 100%; background: #0284C7; color: white; border: none; padding: 6px; border-radius: 4px; cursor: pointer; font-size: 12px; font-weight: 600;">
                    Update Workflow Status
                </button>
            </div>
        `;

        marker.bindPopup(popupContent);
        markersLayer.addLayer(marker);
    });
}

/**
 * Updates the Top Hotspots table
 */
function renderHotspotsTable() {
    const tbody = document.querySelector("#hotspotsTable tbody");
    if (!tbody) return;

    const statusFilter = document.getElementById("statusFilter")?.value || "ALL";
    const typeFilter = document.getElementById("typeFilter")?.value || "ALL";

    const filtered = activeHotspots.filter(h => {
        if (statusFilter !== "ALL" && h.status !== statusFilter) return false;
        if (typeFilter !== "ALL" && h.hazard_type !== typeFilter) return false;
        return true;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center">No ${currentMode.toLowerCase()} hazard reports found matching filters.</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.slice(0, 7).map(h => `
        <tr>
            <td>
                <strong>${h.location_name || "Road Obstacle"}</strong>
                <span style="font-size:9px; color:${h.mode==='HARDWARE'?'#34D399':'#FBBF24'}; margin-left:4px;">[${h.mode}]</span>
            </td>
            <td>${h.hazard_type}</td>
            <td>${h.distinct_rides} passes</td>
            <td><span class="alert-badge badge-${h.priority_level.toLowerCase()}">${h.priority_score}</span></td>
            <td>
                <span class="status-tag status-${h.status.toLowerCase()}" 
                      style="cursor:pointer;" 
                      onclick="openStatusModal(${h.id}, '${h.location_name}', '${h.status}')" 
                      title="Click to update status">
                    ${h.status}
                </span>
            </td>
        </tr>
    `).join("");
}

/**
 * Renders the Recent Alerts Feed
 */
function renderAlertsStream() {
    const container = document.getElementById("alertsStream");
    if (!container) return;

    if (activeHotspots.length === 0) {
        container.innerHTML = `<div class="empty-state">No hazard alerts currently flagged for ${currentMode.toLowerCase()} mode.</div>`;
        return;
    }

    container.innerHTML = activeHotspots.slice(0, 6).map(h => `
        <div class="alert-item ${h.hazard_type.toLowerCase()}">
            <div>
                <div class="alert-title">
                    ${h.hazard_type}: ${h.location_name || "Road Obstacle"}
                    <span style="font-size:9px; color:${h.mode==='HARDWARE'?'#34D399':'#FBBF24'}; margin-left:4px;">[${h.mode}]</span>
                </div>
                <div class="alert-subtitle">${h.distinct_rides} independent buses • ${h.observation_count} detections</div>
            </div>
            <span class="alert-badge badge-${h.priority_level.toLowerCase()}">${h.priority_level}</span>
        </div>
    `).join("");
}

/**
 * Status Transition Modal Functions
 */
function openStatusModal(id, locationName, currentStatus) {
    document.getElementById("modalHotspotId").value = id;
    document.getElementById("modalHotspotInfo").innerHTML = `Updating hotspot: <strong>${locationName}</strong> (Current: <em>${currentStatus}</em>)`;
    document.getElementById("modalNewStatus").value = currentStatus;
    document.getElementById("statusModal").classList.add("show");
}

function closeStatusModal() {
    document.getElementById("statusModal").classList.remove("show");
}

async function submitStatusUpdate() {
    const id = document.getElementById("modalHotspotId").value;
    const newStatus = document.getElementById("modalNewStatus").value;
    const notes = document.getElementById("modalNotes").value;

    try {
        const res = await fetch(`/api/hotspots/${id}/status`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: newStatus, notes: notes })
        });
        if (res.ok) {
            closeStatusModal();
            refreshDashboard();
        } else {
            alert("Failed to update status.");
        }
    } catch (e) {
        alert("Error connecting to backend.");
    }
}

/**
 * Seeds demo hotspots for hackathon presentation
 */
async function seedPuneDemoHotspots() {
    const btn = document.getElementById("btnSeedDemo");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Seeding...';

    try {
        const res = await fetch("/api/demo/seed", { method: "POST" });
        if (res.ok) {
            // Auto-switch to Simulation or All so seeded items are visible immediately
            const modeSelect = document.getElementById("systemModeSelect");
            if (modeSelect && modeSelect.value === "HARDWARE") {
                modeSelect.value = "ALL";
                currentMode = "ALL";
            }
            refreshDashboard();
        }
    } catch (e) {
        console.error(e);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-database"></i> Seed Pune Hotspots';
    }
}

/**
 * Triggers a live simulated bus run
 */
async function triggerLiveSimulation() {
    const btn = document.getElementById("btnRunSim");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-bus fa-bounce"></i> Simulating Bus...';

    await seedPuneDemoHotspots();

    setTimeout(() => {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-play"></i> Run Bus Simulation';
        map.flyTo([18.5204, 73.8567], 13, { duration: 1.5 });
    }, 1200);
}
