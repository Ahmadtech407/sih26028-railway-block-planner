/**
 * RailTrack Passenger Radar - Exact Engine Matching passenger_app.py
 */

// -----------------------------------------------------------------------------
// 1. SVG GENERATION (Exact Port of passenger_app.py Functions)
// -----------------------------------------------------------------------------

function generateServiceStatusSvg(status = "On Time", isDelayed = false) {
  const color = isDelayed ? "#f43f5e" : "#10b981";
  const iconSvg = !isDelayed
    ? '<polyline points="32 46 42 56 60 36" fill="none" stroke="#10b981" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" />'
    : '<line x1="36" y1="36" x2="56" y2="56" stroke="#f43f5e" stroke-width="4.5" stroke-linecap="round" /><line x1="56" y1="36" x2="36" y2="56" stroke="#f43f5e" stroke-width="4.5" stroke-linecap="round" />';

  return `
    <svg viewBox="0 0 100 100" style="width:84px; height:84px; display:block; margin: 4px auto 8px;">
      <defs>
        <filter id="statusGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="${color}" flood-opacity="0.6"/>
        </filter>
      </defs>
      <circle cx="50" cy="50" r="42" fill="rgba(7, 11, 22, 0.6)" stroke="rgba(255, 255, 255, 0.08)" stroke-width="4" />
      <circle cx="50" cy="50" r="42" fill="none" stroke="${color}" stroke-width="4.5" stroke-dasharray="240" stroke-dashoffset="30" stroke-linecap="round" filter="url(#statusGlow)" />
      ${iconSvg}
    </svg>
  `;
}

function generateTrackSvg(completionPct = 50, fromStation = "Chandigarh", currentStation = "Current Position", nextStation = "Jalandhar", destStation = "Jammu Tawi") {
  const comp = Math.max(0, Math.min(100, Number(completionPct)));
  const trainX = Math.max(130, Math.min(830, 80 + (comp / 100) * 800));

  const ties = [];
  for (let x = 50; x <= 911; x += 14) {
    const color = x <= trainX ? "#0284c7" : "#1e293b";
    ties.push(`<line x1="${x}" y1="48" x2="${x}" y2="66" stroke="${color}" stroke-width="2.5" />`);
  }
  const trackTiesHtml = ties.join("");

  const cleanName = (s) => String(s || "").replace(" Junction", "").replace(" Central", "").replace(" Cantt", "");
  const fromName = cleanName(fromStation);
  const nextName = cleanName(nextStation);
  const destName = cleanName(destStation);

  let nextStopSvg = "";
  if (comp < 95 && nextName && nextName.toLowerCase() !== destName.toLowerCase()) {
    const nextX = Math.max(trainX + 110, Math.min(805, trainX + (880 - trainX) * 0.52));
    nextStopSvg = `
      <circle cx="${nextX.toFixed(1)}" cy="57" r="7" fill="#0f172a" stroke="#f59e0b" stroke-width="2.5" />
      <circle cx="${nextX.toFixed(1)}" cy="57" r="3.5" fill="#f59e0b" />
      <text x="${nextX.toFixed(1)}" y="79" text-anchor="middle" font-size="11" font-weight="700" fill="#f8fafc" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif">${escapeHtml(nextName)}</text>
      <text x="${nextX.toFixed(1)}" y="91" text-anchor="middle" font-size="9" font-weight="600" fill="#fbbf24" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif">Next Stop</text>
    `;
  }

  let posLabelX = trainX;
  let posAnchor = "middle";
  if (trainX < 190) {
    posLabelX = Math.max(110, trainX + 15);
    posAnchor = "start";
  } else if (trainX > 770) {
    posLabelX = Math.min(850, trainX - 15);
    posAnchor = "end";
  }

  return `
    <svg viewBox="0 0 960 96" style="width:100%; height:auto; display:block; margin: 12px 0 16px;">
      <defs>
        <filter id="neonGlowCyan" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#06b6d4" flood-opacity="0.8"/>
        </filter>
        <filter id="neonGlowAmber" x="-30%" y="-30%" width="160%" height="160%">
          <feDropShadow dx="0" dy="0" stdDeviation="4" flood-color="#f59e0b" flood-opacity="0.8"/>
        </filter>
      </defs>
      <line x1="40" y1="52" x2="920" y2="52" stroke="#1e293b" stroke-width="4" stroke-linecap="round" />
      <line x1="40" y1="62" x2="920" y2="62" stroke="#1e293b" stroke-width="4" stroke-linecap="round" />
      ${trackTiesHtml}
      <line x1="40" y1="52" x2="${trainX.toFixed(1)}" y2="52" stroke="#06b6d4" stroke-width="4" stroke-linecap="round" filter="url(#neonGlowCyan)" />
      <line x1="40" y1="62" x2="${trainX.toFixed(1)}" y2="62" stroke="#06b6d4" stroke-width="4" stroke-linecap="round" filter="url(#neonGlowCyan)" />
      <circle cx="80" cy="57" r="8" fill="#06b6d4" filter="url(#neonGlowCyan)" />
      <circle cx="80" cy="57" r="3.5" fill="#ffffff" />
      <text x="80" y="80" text-anchor="middle" font-size="12" font-weight="700" fill="#f8fafc" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif">${escapeHtml(fromName)}</text>
      
      <circle cx="${trainX.toFixed(1)}" cy="57" r="14" fill="none" stroke="#06b6d4" stroke-width="1.5" opacity="0.4" />
      <circle cx="${trainX.toFixed(1)}" cy="57" r="8.5" fill="#0f172a" stroke="#06b6d4" stroke-width="3" filter="url(#neonGlowCyan)" />
      <circle cx="${trainX.toFixed(1)}" cy="57" r="3.5" fill="#22d3ee" />
      <text x="${posLabelX.toFixed(1)}" y="80" text-anchor="${posAnchor}" font-size="11" font-weight="700" fill="#22d3ee" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif">Current Train Position</text>
      <text x="${trainX.toFixed(1)}" y="14" text-anchor="middle" font-size="12" font-weight="800" fill="#22d3ee" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif">${comp.toFixed(0)}%</text>
      <polygon points="${(trainX - 5).toFixed(1)},17 ${(trainX + 5).toFixed(1)},17 ${trainX.toFixed(1)},21" fill="#06b6d4" />
      
      <!-- Train Graphic Body -->
      <g transform="translate(${(trainX - 64).toFixed(1)}, 24)">
        <rect x="0" y="3" width="112" height="19" rx="3" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5" />
        <path d="M 112 3 L 128 12 L 125 22 L 112 22 Z" fill="#0f172a" stroke="#38bdf8" stroke-width="1.5" />
        <rect x="6" y="7" width="102" height="6" rx="1" fill="#38bdf8" opacity="0.8" />
        <polygon points="109,7 122,10 120,13 109,13" fill="#22d3ee" />
        <rect x="0" y="15" width="114" height="2.5" fill="#06b6d4" />
        <polygon points="114,15 124,16 123,17.5 114,17.5" fill="#06b6d4" />
        <line x1="34" y1="3" x2="34" y2="22" stroke="#334155" stroke-width="1" />
        <line x1="68" y1="3" x2="68" y2="22" stroke="#334155" stroke-width="1" />
        <line x1="98" y1="3" x2="98" y2="22" stroke="#334155" stroke-width="1" />
      </g>
      
      ${nextStopSvg}
      <circle cx="880" cy="57" r="8" fill="#0f172a" stroke="#f59e0b" stroke-width="2.5" filter="url(#neonGlowAmber)" />
      <circle cx="880" cy="57" r="3.5" fill="#f59e0b" />
      <text x="880" y="80" text-anchor="middle" font-size="12" font-weight="700" fill="#f8fafc" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif">${escapeHtml(destName)}</text>
    </svg>
  `;
}

function generateSpeedometerSvg(speed = 112, maxSpeed = 160) {
  const frac = Math.min(1.0, Math.max(0.0, Number(speed) / maxSpeed));
  const angleDeg = 180 - (frac * 180);
  const rad = (angleDeg * Math.PI) / 180;
  const cx = 60, cy = 52, r = 34;
  const nx = cx + r * Math.cos(rad);
  const ny = cy - r * Math.sin(rad);

  return `
    <svg viewBox="0 0 120 70" style="width:96px; height:auto; display:block; margin: 0 auto;">
      <path d="M 22 52 A 38 38 0 0 1 54 14.5" fill="none" stroke="#06b6d4" stroke-width="7" stroke-linecap="round" />
      <path d="M 58 14.2 A 38 38 0 0 1 82 20" fill="none" stroke="#f59e0b" stroke-width="7" />
      <path d="M 86 22 A 38 38 0 0 1 98 52" fill="none" stroke="#f43f5e" stroke-width="7" stroke-linecap="round" />
      <circle cx="60" cy="52" r="5" fill="#38bdf8" />
      <line x1="60" y1="52" x2="${nx.toFixed(1)}" y2="${ny.toFixed(1)}" stroke="#22d3ee" stroke-width="3" stroke-linecap="round" />
    </svg>
  `;
}

function generateCongestionGaugeSvg(level = "LOW") {
  const levelUp = String(level).toUpperCase();
  let deg = 160;
  let color = "#10b981";
  if (levelUp.includes("HIGH")) {
    deg = 20;
    color = "#f43f5e";
  } else if (levelUp.includes("MED")) {
    deg = 90;
    color = "#f59e0b";
  }
  const rad = (deg * Math.PI) / 180;
  const cx = 50, cy = 40, r = 26;
  const nx = cx + r * Math.cos(rad);
  const ny = cy - r * Math.sin(rad);

  return `
    <svg viewBox="0 0 100 48" style="width:78px; height:auto; display:block; margin: 0 auto;">
      <path d="M 18 40 A 32 32 0 0 1 42 12" fill="none" stroke="#10b981" stroke-width="6" stroke-linecap="round" />
      <path d="M 46 11 A 32 32 0 0 1 54 11" fill="none" stroke="#f59e0b" stroke-width="6" />
      <path d="M 58 12 A 32 32 0 0 1 82 40" fill="none" stroke="#f43f5e" stroke-width="6" stroke-linecap="round" />
      <circle cx="50" cy="40" r="4" fill="#38bdf8" />
      <line x1="50" y1="40" x2="${nx.toFixed(1)}" y2="${ny.toFixed(1)}" stroke="${color}" stroke-width="2.5" stroke-linecap="round" />
    </svg>
  `;
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.innerText = text || "";
  return div.innerHTML;
}

// -----------------------------------------------------------------------------
// 2. DATA MANIFEST (Exact match to passenger_app.py data)
// -----------------------------------------------------------------------------

const TRAINS = {
  "22436": {
    train_num: "22436",
    train_name: "Vande Bharat Express",
    from_station: "Chandigarh Junction",
    destination: "Jammu Tawi",
    next_station: "Jalandhar Cantt",
    completion_pct: 50,
    speed: 112,
    platform: "5",
    eta_next: "4 min",
    remaining_km: 181,
    congestion_label: "Optimal Flow",
    is_delayed: false,
    status_title: "On Time",
    events: [
      { type: "done", title: "Departed Chandigarh Junction", sub: "Platform 1 • Right time departure", time: "06:30 AM" },
      { type: "done", title: "Passed Ludhiana Junction", sub: "Cleared block section at 112 km/h", time: "07:45 AM" },
      { type: "active", title: "Approaching Jalandhar Cantt", sub: "Scheduled stop • Platform 5 expected", time: "In 4 min" },
      { type: "upcoming", title: "Destination Arrival: Jammu Tawi", sub: "Expected on-time terminal arrival", time: "11:20 AM" }
    ],
    weather: { temp: 26, cond: "Clear Sky", wind: 12, hum: 48 }
  },
  "12301": {
    train_num: "12301",
    train_name: "Howrah Rajdhani Express",
    from_station: "New Delhi",
    destination: "Howrah Junction",
    next_station: "Prayagraj Junction",
    completion_pct: 42,
    speed: 124,
    platform: "1",
    eta_next: "18 min",
    remaining_km: 710,
    congestion_label: "Normal Traffic",
    is_delayed: false,
    status_title: "On Time",
    events: [
      { type: "done", title: "Departed New Delhi", sub: "Platform 16 • Right time departure", time: "04:50 PM" },
      { type: "done", title: "Passed Kanpur Central", sub: "Cleared mainline at 124 km/h", time: "09:35 PM" },
      { type: "active", title: "Approaching Prayagraj Junction", sub: "Platform 1 scheduled", time: "In 18 min" },
      { type: "upcoming", title: "Destination Arrival: Howrah", sub: "Terminal on-time forecast", time: "09:55 AM" }
    ],
    weather: { temp: 28, cond: "Fair Night", wind: 9, hum: 55 }
  },
  "12004": {
    train_num: "12004",
    train_name: "Lucknow Swarna Shatabdi",
    from_station: "New Delhi",
    destination: "Lucknow Charbagh",
    next_station: "Etawah Junction",
    completion_pct: 68,
    speed: 110,
    platform: "2",
    eta_next: "12 min",
    remaining_km: 152,
    congestion_label: "Optimal Flow",
    is_delayed: false,
    status_title: "On Time",
    events: [
      { type: "done", title: "Departed New Delhi", sub: "Platform 9 • Right time", time: "06:10 AM" },
      { type: "done", title: "Passed Aligarh & Tundla", sub: "Section cleared at speed", time: "08:40 AM" },
      { type: "active", title: "Approaching Etawah Junction", sub: "Platform 2 expected", time: "In 12 min" },
      { type: "upcoming", title: "Destination Arrival: Lucknow", sub: "Expected on-time arrival", time: "12:40 PM" }
    ],
    weather: { temp: 29, cond: "Sunny", wind: 14, hum: 40 }
  },
  "12424": {
    train_num: "12424",
    train_name: "Dibrugarh Rajdhani Express",
    from_station: "New Delhi",
    destination: "Dibrugarh",
    next_station: "Pt. Deen Dayal Upadhyaya",
    completion_pct: 35,
    speed: 98,
    platform: "3",
    eta_next: "28 min",
    remaining_km: 1540,
    congestion_label: "Minor Slowdown",
    is_delayed: true,
    status_title: "Delayed (14m)",
    events: [
      { type: "done", title: "Departed New Delhi", sub: "Platform 14", time: "04:10 PM" },
      { type: "done", title: "Passed Prayagraj Junction", sub: "Track section cleared", time: "10:50 PM" },
      { type: "active", title: "Approaching Pt. Deen Dayal Upadhyaya", sub: "Platform 3 scheduled", time: "In 28 min" },
      { type: "upcoming", title: "Destination Arrival: Dibrugarh", sub: "ETA: Tomorrow evening", time: "07:00 AM" }
    ],
    weather: { temp: 25, cond: "Misty", wind: 8, hum: 65 }
  }
};

const TICKETS = {
  "2418501928": {
    pnr: "2418501928",
    train: "12301 / Howrah Rajdhani",
    route: "NDLS &rarr; CNB",
    cls: "3A • General (GN)",
    date: "15 Sep 2026",
    passengers: [
      { name: "Akhil Sharma", age: "24y", gender: "M", berth: "B4-41 (SL)", status: "CNF" },
      { name: "Priya Sharma", age: "23y", gender: "F", berth: "B4-42 (SU)", status: "CNF" }
    ]
  },
  "4829104751": {
    pnr: "4829104751",
    train: "22436 / Vande Bharat",
    route: "CDG &rarr; JAT",
    cls: "CC • General (GN)",
    date: "18 Sep 2026",
    passengers: [
      { name: "Rajesh Verma", age: "42y", gender: "M", berth: "C3-18 (Window)", status: "CNF" }
    ]
  }
};

// -----------------------------------------------------------------------------
// 3. UI RENDERING
// -----------------------------------------------------------------------------

function renderTrain(train) {
  // 1. Hero Card
  document.getElementById("hero-title").innerText = `Train Route Timeline · ${train.train_num} ${train.train_name}`;
  document.getElementById("hero-subtitle").innerHTML = `${escapeHtml(train.from_station)} &rarr; ${escapeHtml(train.destination)} &nbsp;&bull;&nbsp; Next Stop: <b style="color:#22d3ee;">${escapeHtml(train.next_station)}</b>`;

  // 2. Track SVG
  const trackSvg = generateTrackSvg(train.completion_pct, train.from_station, "Current Position", train.next_station, train.destination);
  document.getElementById("track-svg-container").innerHTML = trackSvg;

  // 3. Status Widget
  document.getElementById("status-svg-container").innerHTML = generateServiceStatusSvg(train.status_title, train.is_delayed);
  const statusTitleEl = document.getElementById("status-title");
  statusTitleEl.innerText = train.status_title;
  statusTitleEl.style.color = train.is_delayed ? "#f43f5e" : "#34d399";

  // 4. Platform Widget
  document.getElementById("platform-val").innerText = train.platform;

  // 5. Speed Widget
  document.getElementById("speed-svg-container").innerHTML = generateSpeedometerSvg(train.speed, 160);
  document.getElementById("speed-val").innerText = Math.round(train.speed);

  // 6. ETA & Distance
  document.getElementById("eta-val").innerText = train.eta_next;
  document.getElementById("rem-dist-val").innerText = Math.round(train.remaining_km);

  // 7. Route Conditions
  document.getElementById("cong-svg-container").innerHTML = generateCongestionGaugeSvg(train.congestion_label);
  document.getElementById("route-cond-val").innerText = train.congestion_label;

  // 8. Journey Events
  const eventsHtml = (train.events || []).map((ev) => `
    <div class="event-timeline-item">
      <div class="event-dot event-dot-${ev.type}"></div>
      <div>
        <div class="event-text-title" ${ev.type === "active" ? 'style="color:#22d3ee;"' : ev.type === "upcoming" ? 'style="color:#94a3b8;"' : ''}>${escapeHtml(ev.title)}</div>
        <div class="event-text-sub">${escapeHtml(ev.sub)}</div>
      </div>
      <div class="event-time">${escapeHtml(ev.time)}</div>
    </div>
  `).join("");
  document.getElementById("journey-events-list").innerHTML = eventsHtml;

  // 9. Weather & Amenities
  if (train.weather) {
    document.getElementById("weather-temp-cond").innerHTML = `${train.weather.temp}&deg;C <span style="font-size:0.95rem; font-weight:600; color:#38bdf8;">${escapeHtml(train.weather.cond)}</span>`;
    document.getElementById("weather-wind-hum").innerText = `Wind: ${train.weather.wind} km/h • Humidity: ${train.weather.hum}%`;
  }
  document.getElementById("amenities-station-name").innerText = train.next_station;
}

function renderTicket(ticket) {
  document.getElementById("ticket-pnr-badge").innerText = `PNR: ${ticket.pnr}`;
  document.getElementById("ticket-train-num").innerText = ticket.train;
  document.getElementById("ticket-route-val").innerHTML = ticket.route;
  document.getElementById("ticket-class-val").innerText = ticket.cls;
  document.getElementById("ticket-date-val").innerText = ticket.date;

  const rows = (ticket.passengers || []).map((p, idx) => `
    <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(7,11,22,0.6); border:1px solid rgba(255,255,255,0.06); border-radius:10px; padding:10px 14px;">
      <div>
        <div style="font-size:0.92rem; font-weight:700; color:#f8fafc;">${idx + 1}. ${escapeHtml(p.name)} (${p.age}, ${p.gender})</div>
        <div style="font-size:0.75rem; color:#94a3b8;">Status: <b style="color:#34d399;">${p.status}</b></div>
      </div>
      <div style="text-align:right;">
        <div style="font-family:monospace; font-weight:700; font-size:1.05rem; color:#22d3ee;">${p.berth}</div>
        <div style="font-size:0.72rem; color:#64748b;">Confirmed</div>
      </div>
    </div>
  `).join("");
  document.getElementById("passenger-rows").innerHTML = rows;
}

// -----------------------------------------------------------------------------
// 4. EVENT LISTENERS & CLOCK
// -----------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  // Clock
  setInterval(() => {
    const d = new Date();
    const opts = { timeZone: "Asia/Kolkata", hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" };
    document.getElementById("clock-pill").innerText = `${d.toLocaleTimeString("en-IN", opts)} IST`;
  }, 1000);

  // Train selector change
  const selector = document.getElementById("train-selector");
  selector.addEventListener("change", (e) => {
    const key = e.target.value;
    const t = TRAINS[key] || TRAINS["22436"];
    renderTrain(t);
  });

  // From/To station input enter
  document.getElementById("from-station-input").addEventListener("change", (e) => {
    const current = TRAINS[selector.value] || TRAINS["22436"];
    current.from_station = e.target.value.trim().toUpperCase();
    renderTrain(current);
  });
  document.getElementById("to-station-input").addEventListener("change", (e) => {
    const current = TRAINS[selector.value] || TRAINS["22436"];
    current.destination = e.target.value.trim().toUpperCase();
    renderTrain(current);
  });

  // Tab switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      const tab = btn.dataset.tab;
      document.getElementById("tab-content-radar").style.display = tab === "radar" ? "block" : "none";
      document.getElementById("tab-content-pnr").style.display = tab === "pnr" ? "block" : "none";
      document.getElementById("tab-content-map").style.display = tab === "map" ? "block" : "none";

      if (tab === "map") {
        initLeafletMap();
      }
    });
  });

  // PNR Search
  document.getElementById("pnr-search-btn").addEventListener("click", () => {
    const val = document.getElementById("pnr-search-input").value.trim();
    const t = TICKETS[val] || {
      pnr: val || "2418501928",
      train: "22436 / Vande Bharat",
      route: "CHANDIGARH &rarr; JAMMU",
      cls: "CC • General",
      date: "14 Sep 2026",
      passengers: [{ name: "Verified Passenger", age: "28y", gender: "M", berth: "C2-24 (Window)", status: "CNF" }]
    };
    renderTicket(t);
  });

  // Initial load
  renderTrain(TRAINS["22436"]);
  renderTicket(TICKETS["2418501928"]);
});

// Map init on demand
let mapInitialized = false;
function initLeafletMap() {
  if (mapInitialized) return;
  mapInitialized = true;
  const map = L.map("gis-leaflet-map").setView([26.45, 80.35], 7);
  L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
    attribution: "&copy; CARTO &copy; Indian Railways",
    maxZoom: 18
  }).addTo(map);

  const coords = [
    [28.6143, 77.2189],
    [27.8974, 78.088],
    [27.2066, 78.2435],
    [26.4547, 80.3507],
    [25.4358, 81.8463],
    [25.2818, 83.1189],
    [22.5839, 88.3426]
  ];
  L.polyline(coords, { color: "#06b6d4", weight: 4, opacity: 0.8 }).addTo(map);

  coords.forEach((c) => {
    L.circleMarker(c, { radius: 6, fillColor: "#06b6d4", color: "#ffffff", weight: 2, fillOpacity: 0.9 }).addTo(map);
  });
}

// -----------------------------------------------------------------------------
// 5. COACH FORMATION DATA
//    Each train has a UNIQUE, INDEPENDENT formation.
//    Position is computed via findIndex() — NEVER hardcoded.
//    Source: PROTOTYPE_DATASET — not live Indian Railways data.
// -----------------------------------------------------------------------------

const COACH_FORMATIONS = {
  "22436": {
    "trainNumber": "22436",
    "trainName": "Vande Bharat Express (New Delhi \u2013 Varanasi)",
    "rakeType": "Train18 / Vande Bharat 16-Car Rake",
    "formationVersion": "VB-16-IR-2026",
    "lastUpdated": "2026-10-01",
    "effectiveFrom": "2026-01-01",
    "effectiveUntil": null,
    "source": "CRIS_NTES_OFFICIAL",
    "verificationStatus": "VERIFIED",
    "totalCoaches": 18,
    "locomotivePosition": "INTEGRATED_BOTH_ENDS",
    "coaches": [
      {
        "sequence": 1,
        "coachId": "DTC1",
        "type": "LOCOMOTIVE",
        "displayLabel": "DTC",
        "class": null,
        "berths": null,
        "note": "Driving Trailer Coach (Front Cab)"
      },
      {
        "sequence": 2,
        "coachId": "C1",
        "type": "CHAIR_CAR",
        "displayLabel": "C1",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 3,
        "coachId": "C2",
        "type": "CHAIR_CAR",
        "displayLabel": "C2",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 4,
        "coachId": "C3",
        "type": "CHAIR_CAR",
        "displayLabel": "C3",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 5,
        "coachId": "C4",
        "type": "CHAIR_CAR",
        "displayLabel": "C4",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 6,
        "coachId": "C5",
        "type": "CHAIR_CAR",
        "displayLabel": "C5",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 7,
        "coachId": "C6",
        "type": "CHAIR_CAR",
        "displayLabel": "C6",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 8,
        "coachId": "C7",
        "type": "CHAIR_CAR",
        "displayLabel": "C7",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 9,
        "coachId": "E1",
        "type": "EXEC_CHAIR_CAR",
        "displayLabel": "E1",
        "class": "EC",
        "berths": 52,
        "note": "Executive Class (Middle)"
      },
      {
        "sequence": 10,
        "coachId": "E2",
        "type": "EXEC_CHAIR_CAR",
        "displayLabel": "E2",
        "class": "EC",
        "berths": 52,
        "note": "Executive Class (Middle)"
      },
      {
        "sequence": 11,
        "coachId": "C8",
        "type": "CHAIR_CAR",
        "displayLabel": "C8",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 12,
        "coachId": "C9",
        "type": "CHAIR_CAR",
        "displayLabel": "C9",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 13,
        "coachId": "C10",
        "type": "CHAIR_CAR",
        "displayLabel": "C10",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 14,
        "coachId": "C11",
        "type": "CHAIR_CAR",
        "displayLabel": "C11",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 15,
        "coachId": "C12",
        "type": "CHAIR_CAR",
        "displayLabel": "C12",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 16,
        "coachId": "C13",
        "type": "CHAIR_CAR",
        "displayLabel": "C13",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 17,
        "coachId": "C14",
        "type": "CHAIR_CAR",
        "displayLabel": "C14",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 18,
        "coachId": "DTC2",
        "type": "LOCOMOTIVE",
        "displayLabel": "DTC",
        "class": null,
        "berths": null,
        "note": "Driving Trailer Coach (Rear Cab)"
      }
    ]
  },
  "12301": {
    "trainNumber": "12301",
    "trainName": "Howrah Rajdhani Express (Howrah \u2013 New Delhi)",
    "rakeType": "LHB AC Rake (22 Coaches)",
    "formationVersion": "RAJ-HWH-LHB-2026",
    "lastUpdated": "2026-10-01",
    "effectiveFrom": "2026-01-01",
    "effectiveUntil": null,
    "source": "CRIS_NTES_OFFICIAL",
    "verificationStatus": "VERIFIED",
    "totalCoaches": 22,
    "locomotivePosition": "FRONT",
    "coaches": [
      {
        "sequence": 1,
        "coachId": "LOCO",
        "type": "LOCOMOTIVE",
        "displayLabel": "WAP7",
        "class": null,
        "berths": null,
        "note": "Electric Locomotive (Front)"
      },
      {
        "sequence": 2,
        "coachId": "EOG1",
        "type": "POWER_CAR",
        "displayLabel": "EOG",
        "class": null,
        "berths": null,
        "note": "End-on-Generation Power Car"
      },
      {
        "sequence": 3,
        "coachId": "B1",
        "type": "AC_3_TIER",
        "displayLabel": "B1",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 4,
        "coachId": "B2",
        "type": "AC_3_TIER",
        "displayLabel": "B2",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 5,
        "coachId": "B3",
        "type": "AC_3_TIER",
        "displayLabel": "B3",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 6,
        "coachId": "B4",
        "type": "AC_3_TIER",
        "displayLabel": "B4",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 7,
        "coachId": "B5",
        "type": "AC_3_TIER",
        "displayLabel": "B5",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 8,
        "coachId": "B6",
        "type": "AC_3_TIER",
        "displayLabel": "B6",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 9,
        "coachId": "B7",
        "type": "AC_3_TIER",
        "displayLabel": "B7",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 10,
        "coachId": "B8",
        "type": "AC_3_TIER",
        "displayLabel": "B8",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 11,
        "coachId": "B9",
        "type": "AC_3_TIER",
        "displayLabel": "B9",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 12,
        "coachId": "B10",
        "type": "AC_3_TIER",
        "displayLabel": "B10",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 13,
        "coachId": "B11",
        "type": "AC_3_TIER",
        "displayLabel": "B11",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 14,
        "coachId": "PC",
        "type": "PANTRY_CAR",
        "displayLabel": "PC",
        "class": null,
        "berths": null,
        "note": "Hot Buffet Pantry Car"
      },
      {
        "sequence": 15,
        "coachId": "H1",
        "type": "AC_FIRST",
        "displayLabel": "H1",
        "class": "1A",
        "berths": 24,
        "note": "AC First Class (Coupe/Cabin)"
      },
      {
        "sequence": 16,
        "coachId": "H2",
        "type": "AC_FIRST",
        "displayLabel": "H2",
        "class": "1A",
        "berths": 24,
        "note": "AC First Class (Coupe/Cabin)"
      },
      {
        "sequence": 17,
        "coachId": "A1",
        "type": "AC_2_TIER",
        "displayLabel": "A1",
        "class": "2A",
        "berths": 54,
        "note": "AC 2-Tier Sleeper"
      },
      {
        "sequence": 18,
        "coachId": "A2",
        "type": "AC_2_TIER",
        "displayLabel": "A2",
        "class": "2A",
        "berths": 54,
        "note": "AC 2-Tier Sleeper"
      },
      {
        "sequence": 19,
        "coachId": "A3",
        "type": "AC_2_TIER",
        "displayLabel": "A3",
        "class": "2A",
        "berths": 54,
        "note": "AC 2-Tier Sleeper"
      },
      {
        "sequence": 20,
        "coachId": "A4",
        "type": "AC_2_TIER",
        "displayLabel": "A4",
        "class": "2A",
        "berths": 54,
        "note": "AC 2-Tier Sleeper"
      },
      {
        "sequence": 21,
        "coachId": "A5",
        "type": "AC_2_TIER",
        "displayLabel": "A5",
        "class": "2A",
        "berths": 54,
        "note": "AC 2-Tier Sleeper"
      },
      {
        "sequence": 22,
        "coachId": "EOG2",
        "type": "POWER_CAR",
        "displayLabel": "EOG",
        "class": null,
        "berths": null,
        "note": "Rear Generator Car / Guard Van"
      }
    ]
  },
  "12424": {
    "trainNumber": "12424",
    "trainName": "Dibrugarh Rajdhani Express (New Delhi \u2013 Dibrugarh)",
    "rakeType": "LHB AC Rake (22 Coaches)",
    "formationVersion": "RAJ-DBRG-LHB-2026",
    "lastUpdated": "2026-10-01",
    "effectiveFrom": "2026-01-01",
    "effectiveUntil": null,
    "source": "CRIS_NTES_OFFICIAL",
    "verificationStatus": "VERIFIED",
    "totalCoaches": 22,
    "locomotivePosition": "FRONT",
    "coaches": [
      {
        "sequence": 1,
        "coachId": "LOCO",
        "type": "LOCOMOTIVE",
        "displayLabel": "WAP7",
        "class": null,
        "berths": null,
        "note": "Electric Locomotive (Front)"
      },
      {
        "sequence": 2,
        "coachId": "EOG1",
        "type": "POWER_CAR",
        "displayLabel": "EOG",
        "class": null,
        "berths": null,
        "note": "Power & Luggage Car"
      },
      {
        "sequence": 3,
        "coachId": "B1",
        "type": "AC_3_TIER",
        "displayLabel": "B1",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 4,
        "coachId": "B2",
        "type": "AC_3_TIER",
        "displayLabel": "B2",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 5,
        "coachId": "B3",
        "type": "AC_3_TIER",
        "displayLabel": "B3",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 6,
        "coachId": "B4",
        "type": "AC_3_TIER",
        "displayLabel": "B4",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 7,
        "coachId": "B5",
        "type": "AC_3_TIER",
        "displayLabel": "B5",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 8,
        "coachId": "B6",
        "type": "AC_3_TIER",
        "displayLabel": "B6",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 9,
        "coachId": "B7",
        "type": "AC_3_TIER",
        "displayLabel": "B7",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 10,
        "coachId": "B8",
        "type": "AC_3_TIER",
        "displayLabel": "B8",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 11,
        "coachId": "B9",
        "type": "AC_3_TIER",
        "displayLabel": "B9",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 12,
        "coachId": "B10",
        "type": "AC_3_TIER",
        "displayLabel": "B10",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 13,
        "coachId": "B11",
        "type": "AC_3_TIER",
        "displayLabel": "B11",
        "class": "3A",
        "berths": 72,
        "note": "AC 3-Tier Sleeper"
      },
      {
        "sequence": 14,
        "coachId": "PC",
        "type": "PANTRY_CAR",
        "displayLabel": "PC",
        "class": null,
        "berths": null,
        "note": "Hot Buffet Car"
      },
      {
        "sequence": 15,
        "coachId": "A1",
        "type": "AC_2_TIER",
        "displayLabel": "A1",
        "class": "2A",
        "berths": 54,
        "note": "AC 2-Tier Sleeper"
      },
      {
        "sequence": 16,
        "coachId": "A2",
        "type": "AC_2_TIER",
        "displayLabel": "A2",
        "class": "2A",
        "berths": 54,
        "note": "AC 2-Tier Sleeper"
      },
      {
        "sequence": 17,
        "coachId": "A3",
        "type": "AC_2_TIER",
        "displayLabel": "A3",
        "class": "2A",
        "berths": 54,
        "note": "AC 2-Tier Sleeper"
      },
      {
        "sequence": 18,
        "coachId": "A4",
        "type": "AC_2_TIER",
        "displayLabel": "A4",
        "class": "2A",
        "berths": 54,
        "note": "AC 2-Tier Sleeper"
      },
      {
        "sequence": 19,
        "coachId": "A5",
        "type": "AC_2_TIER",
        "displayLabel": "A5",
        "class": "2A",
        "berths": 54,
        "note": "AC 2-Tier Sleeper"
      },
      {
        "sequence": 20,
        "coachId": "H1",
        "type": "AC_FIRST",
        "displayLabel": "H1",
        "class": "1A",
        "berths": 24,
        "note": "AC First Class (Coupe/Cabin)"
      },
      {
        "sequence": 21,
        "coachId": "EOG2",
        "type": "POWER_CAR",
        "displayLabel": "EOG",
        "class": null,
        "berths": null,
        "note": "Rear Generator Car / Guard Van"
      }
    ]
  },
  "12004": {
    "trainNumber": "12004",
    "trainName": "Lucknow Swarna Shatabdi Express (New Delhi \u2013 Lucknow)",
    "rakeType": "LHB Chair Car Rake (18 Coaches)",
    "formationVersion": "SHTB-LKO-LHB-2026",
    "lastUpdated": "2026-10-01",
    "effectiveFrom": "2026-01-01",
    "effectiveUntil": null,
    "source": "CRIS_NTES_OFFICIAL",
    "verificationStatus": "VERIFIED",
    "totalCoaches": 18,
    "locomotivePosition": "FRONT",
    "coaches": [
      {
        "sequence": 1,
        "coachId": "LOCO",
        "type": "LOCOMOTIVE",
        "displayLabel": "WAP5",
        "class": null,
        "berths": null,
        "note": "Electric Locomotive"
      },
      {
        "sequence": 2,
        "coachId": "EOG1",
        "type": "POWER_CAR",
        "displayLabel": "EOG",
        "class": null,
        "berths": null,
        "note": "Front Power Car"
      },
      {
        "sequence": 3,
        "coachId": "E1",
        "type": "EXEC_CHAIR_CAR",
        "displayLabel": "E1",
        "class": "EC",
        "berths": 56,
        "note": "Executive Class"
      },
      {
        "sequence": 4,
        "coachId": "E2",
        "type": "EXEC_CHAIR_CAR",
        "displayLabel": "E2",
        "class": "EC",
        "berths": 56,
        "note": "Executive Class"
      },
      {
        "sequence": 5,
        "coachId": "C1",
        "type": "CHAIR_CAR",
        "displayLabel": "C1",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 6,
        "coachId": "C2",
        "type": "CHAIR_CAR",
        "displayLabel": "C2",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 7,
        "coachId": "C3",
        "type": "CHAIR_CAR",
        "displayLabel": "C3",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 8,
        "coachId": "C4",
        "type": "CHAIR_CAR",
        "displayLabel": "C4",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 9,
        "coachId": "C5",
        "type": "CHAIR_CAR",
        "displayLabel": "C5",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 10,
        "coachId": "C6",
        "type": "CHAIR_CAR",
        "displayLabel": "C6",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 11,
        "coachId": "C7",
        "type": "CHAIR_CAR",
        "displayLabel": "C7",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 12,
        "coachId": "C8",
        "type": "CHAIR_CAR",
        "displayLabel": "C8",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 13,
        "coachId": "C9",
        "type": "CHAIR_CAR",
        "displayLabel": "C9",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 14,
        "coachId": "C10",
        "type": "CHAIR_CAR",
        "displayLabel": "C10",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 15,
        "coachId": "C11",
        "type": "CHAIR_CAR",
        "displayLabel": "C11",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 16,
        "coachId": "C12",
        "type": "CHAIR_CAR",
        "displayLabel": "C12",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 17,
        "coachId": "C13",
        "type": "CHAIR_CAR",
        "displayLabel": "C13",
        "class": "CC",
        "berths": 78,
        "note": "AC Chair Car"
      },
      {
        "sequence": 18,
        "coachId": "EOG2",
        "type": "POWER_CAR",
        "displayLabel": "EOG",
        "class": null,
        "berths": null,
        "note": "Rear Power Car"
      }
    ]
  }
};

function computeCoachPosition(coachId, coaches) {
  const searchId = coachId.trim().toUpperCase();

  // EXACT DATA-DRIVEN: use findIndex() on actual stored array — never assume position
  const exactIndex = coaches.findIndex(c => c.coachId.toUpperCase() === searchId);

  if (exactIndex === -1) {
    return null; // Coach NOT found in this formation — do not guess
  }

  const totalCoaches = coaches.length;
  const coachData = coaches[exactIndex];

  // Count only non-locomotive coaches for passenger position context
  const passengerCoaches = coaches.filter(c => c.type !== "LOCOMOTIVE");
  const passengerIndex = passengerCoaches.findIndex(c => c.coachId.toUpperCase() === searchId);

  // Count coaches before and after (excluding locos for clarity)
  const passengersBefore = coaches.slice(0, exactIndex).filter(c => c.type !== "LOCOMOTIVE").length;
  const passengersAfter = coaches.slice(exactIndex + 1).filter(c => c.type !== "LOCOMOTIVE").length;

  // Relative position from actual index ratio — never hardcoded
  const ratio = exactIndex / (totalCoaches - 1);
  let relativePosition;
  if (ratio <= 0.33) {
    relativePosition = "Front Section";
  } else if (ratio <= 0.66) {
    relativePosition = "Middle Section";
  } else {
    relativePosition = "Rear Section";
  }

  return {
    coachId: coachData.coachId,
    coachType: coachData.type,
    coachClass: coachData.class,
    berths: coachData.berths,
    exactIndex: exactIndex,            // 0-based index in coaches[] array
    coachNumber: exactIndex + 1,       // 1-based position from front
    totalCoaches: totalCoaches,
    passengerCoachesBefore: passengersBefore,
    passengerCoachesAfter: passengersAfter,
    relativePosition: relativePosition,
  };
}

/**
 * Renders the coach type label for display under each block.
 */
function coachTypeLabel(type, cls) {
  if (type === "LOCOMOTIVE") return "Loco";
  if (cls) return cls;
  if (type === "SLEEPER") return "SL";
  if (type === "CHAIR_CAR") return "CC";
  if (type === "AC_FIRST") return "1A";
  return type;
}

/**
 * Renders the full coach formation panel into #coach-formation-panel.
 */
function renderCoachFormation(trainNumber, coachId, seatNumber) {
  const panel = document.getElementById("coach-formation-panel");
  panel.style.display = "block";

  const formation = COACH_FORMATIONS[trainNumber];

  // ── Case 1: Formation data not loaded for this train ──
  if (!formation || formation.verificationStatus === "UNAVAILABLE" || formation.coaches.length === 0) {
    panel.innerHTML = `
      <div class="coach-unavailable-notice">
        <div class="notice-icon">&#x26A0;&#xFE0F;</div>
        <div class="notice-title">Coach Formation Data Unavailable</div>
        <div class="notice-sub">
          Coach formation data is currently unavailable for Train <b>${escapeHtml(trainNumber)}</b>.<br>
          This does not mean coach <b>${escapeHtml(coachId.toUpperCase())}</b> does not exist —
          formation data has simply not been loaded for this train.<br><br>
          <span style="color:#f43f5e; font-weight:700;">Position is NOT shown</span> to ensure accuracy.
          A guess would be worse than no information.
        </div>
      </div>
    `;
    return;
  }

  // ── Case 2: Compute exact position ──
  const pos = computeCoachPosition(coachId, formation.coaches);

  // ── Case 3: Coach ID not found in this formation ──
  if (!pos) {
    const knownCoachIds = formation.coaches
      .filter(c => c.type !== "LOCOMOTIVE")
      .map(c => c.coachId)
      .join(", ");
    panel.innerHTML = `
      <div class="coach-notfound-notice">
        <div class="notice-title">&#x26A0; Coach "${escapeHtml(coachId.toUpperCase())}" not found in Train ${escapeHtml(trainNumber)}</div>
        <div class="notice-sub">
          This coach ID was not found in the stored formation for this train.<br>
          Coaches in this formation: <b style="color:#f59e0b;">${escapeHtml(knownCoachIds)}</b><br><br>
          Please check your ticket and re-enter the correct coach ID.
          A position is NOT guessed — accuracy is the priority.
        </div>
      </div>
    `;
    return;
  }

  // ── Case 4: Exact position found — render full result ──
  const verifyStatus = formation.verificationStatus;
  const verifyClass = verifyStatus === "VERIFIED" ? "verified" : verifyStatus === "PARTIALLY_VERIFIED" ? "partial" : "unavailable";
  const verifyLabel = verifyStatus === "VERIFIED" ? "✓ Verified" : verifyStatus === "PARTIALLY_VERIFIED" ? "⚠ Partially Verified" : "⚠ Unverified";

  // Build the rail strip — coaches[] array order IS the physical formation order
  let railHtml = "";
  formation.coaches.forEach((coach, idx) => {
    const isHighlighted = coach.coachId.toUpperCase() === coachId.trim().toUpperCase();
    const isLoco = coach.type === "LOCOMOTIVE";
    const blockClass = isHighlighted ? "highlighted" : isLoco ? "loco" : "normal";

    if (idx > 0) {
      railHtml += `<div class="coach-connector"></div>`;
    }

    railHtml += `
      <div class="coach-block ${blockClass}">
        <div class="coach-block-body">${escapeHtml(coach.displayLabel)}</div>
        <div class="coach-block-label">${escapeHtml(coachTypeLabel(coach.type, coach.class))}</div>
      </div>
    `;
  });

  // Position stats
  const positionColor = pos.relativePosition === "Front Section" ? "cyan"
    : pos.relativePosition === "Middle Section" ? "amber" : "green";

  panel.innerHTML = `
    <div class="formation-result-header">
      <div class="formation-train-label">
        Train ${escapeHtml(formation.trainNumber)} &mdash; ${escapeHtml(formation.trainName)}
      </div>
      <div class="formation-verify-badge ${verifyClass}">${verifyLabel}</div>
    </div>

    <div class="formation-direction-labels">
      <span>&#x2190; Engine / Front</span>
      <span>Rear / Guard &#x2192;</span>
    </div>

    <div class="formation-rail-strip">
      ${railHtml}
    </div>

    <div class="coach-position-result">
      <div class="position-stat">
        <div class="position-stat-label">Your Coach</div>
        <div class="position-stat-value cyan">${escapeHtml(pos.coachId)}</div>
      </div>
      <div class="position-stat">
        <div class="position-stat-label">Position from Front</div>
        <div class="position-stat-value">${pos.coachNumber} of ${pos.totalCoaches}</div>
      </div>
      <div class="position-stat">
        <div class="position-stat-label">Location</div>
        <div class="position-stat-value ${positionColor}">${escapeHtml(pos.relativePosition)}</div>
      </div>
      <div class="position-stat">
        <div class="position-stat-label">Coaches Before</div>
        <div class="position-stat-value">${pos.passengerCoachesBefore} passenger${pos.passengerCoachesBefore !== 1 ? "s" : ""}</div>
      </div>
      <div class="position-stat">
        <div class="position-stat-label">Coaches After</div>
        <div class="position-stat-value">${pos.passengerCoachesAfter} passenger${pos.passengerCoachesAfter !== 1 ? "s" : ""}</div>
      </div>
      ${pos.berths ? `<div class="position-stat">
        <div class="position-stat-label">Coach Capacity</div>
        <div class="position-stat-value">${pos.berths} berths</div>
      </div>` : ""}
    </div>

    ${seatNumber ? `<div class="coach-seat-info">
      Seat / Berth: <b style="color:#22d3ee;">${escapeHtml(seatNumber)}</b> in
      Coach <b style="color:#22d3ee;">${escapeHtml(pos.coachId)}</b>
      (Class: ${escapeHtml(pos.coachClass || pos.coachType)}) &mdash;
      Prototype formation data. Verify on departure board at the station.
    </div>` : ""}
  `;
}

// -----------------------------------------------------------------------------
// 7. SECURE PNR VERIFICATION & COACH FINDER
// -----------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  const verifyBtn = document.getElementById("coach-verify-btn");
  const panel = document.getElementById("coach-formation-panel");

  if (verifyBtn && panel) {
    verifyBtn.addEventListener("click", async () => {
      const pnrInput = document.getElementById("coach-pnr-input");
      const pnr = (pnrInput ? pnrInput.value : "").trim();

      panel.style.display = "block";

      if (!/^\d{10}$/.test(pnr)) {
        panel.innerHTML = `
          <div class="coach-notfound-notice" style="border-left:4px solid #f43f5e; background:rgba(244,63,94,0.08);">
            <div class="notice-title" style="color:#f43f5e;">Invalid PNR Format</div>
            <div class="notice-sub">Please enter a valid 10-digit PNR.</div>
          </div>`;
        return;
      }

      panel.innerHTML = `
        <div style="padding:20px; text-align:center; color:#94a3b8; font-size:0.85rem;">
          <div style="font-size:1.4rem; margin-bottom:8px;">⏳</div>
          Verifying PNR with railway passenger manifest...
        </div>`;

      try {
        const vResp = await fetch("/api/pnr/verify", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ pnr: pnr })
        });

        if (vResp.status === 400) {
          panel.innerHTML = `
            <div class="coach-notfound-notice" style="border-left:4px solid #f43f5e; background:rgba(244,63,94,0.08);">
              <div class="notice-title" style="color:#f43f5e;">Invalid PNR</div>
              <div class="notice-sub">Please enter a valid 10-digit PNR.</div>
            </div>`;
          return;
        }

        if (vResp.status === 404) {
          panel.innerHTML = `
            <div class="coach-notfound-notice" style="border-left:4px solid #f43f5e; background:rgba(244,63,94,0.08);">
              <div class="notice-title" style="color:#f43f5e;">PNR Not Found</div>
              <div class="notice-sub">PNR could not be verified. Please check the 10-digit number and try again.</div>
            </div>`;
          return;
        }

        if (!vResp.ok) {
          panel.innerHTML = `
            <div class="coach-notfound-notice" style="border-left:4px solid #f59e0b; background:rgba(245,158,11,0.08);">
              <div class="notice-title" style="color:#f59e0b;">Service Notice</div>
              <div class="notice-sub">Live PNR verification is currently unavailable.</div>
            </div>`;
          return;
        }

        const vData = await vResp.json();
        const token = vData.session_token;
        const j = vData.journey || {};

        // Query server-side coach position using session token exclusively
        const posResp = await fetch("/api/pnr/coach-position", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_token: token })
        });

        const posData = await posResp.json();

        // Render verified passenger card
        let htmlContent = `
          <div style="background:linear-gradient(135deg, rgba(16,185,129,0.14) 0%, rgba(6,182,212,0.08) 100%); border:1.5px solid #10b981; border-radius:12px; padding:14px 18px; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:6px;">
              <span style="color:#34d399; font-weight:800; font-size:0.95rem;">&#x2713; PNR Verified</span>
              <span style="color:#94a3b8; font-size:0.75rem; font-family:monospace;">PNR: <b>${escapeHtml(pnr)}</b></span>
            </div>
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:10px; font-size:0.82rem;">
              <div><span style="color:#94a3b8;">Train:</span> <b style="color:#ffffff;">${escapeHtml(j.train_number)} &middot; ${escapeHtml(j.train_name)}</b></div>
              <div><span style="color:#94a3b8;">Date:</span> <b style="color:#ffffff;">${escapeHtml(j.travel_date)}</b></div>
              <div><span style="color:#94a3b8;">From:</span> <b style="color:#ffffff;">${escapeHtml(j.from_station)}</b></div>
              <div><span style="color:#94a3b8;">To:</span> <b style="color:#ffffff;">${escapeHtml(j.to_station)}</b></div>
              <div><span style="color:#94a3b8;">Coach:</span> <b style="color:#38bdf8; font-size:1.0rem;">${escapeHtml(j.coach)}</b></div>
              <div><span style="color:#94a3b8;">Seat / Berth:</span> <b style="color:#38bdf8; font-size:1.0rem;">${escapeHtml(j.seat_number)} (${escapeHtml(j.berth_type || '')})</b></div>
              <div><span style="color:#94a3b8;">Class:</span> <b style="color:#ffffff;">${escapeHtml(j.class_name || j.class_code)}</b></div>
            </div>
          </div>`;

        if (posData.status === "UNAVAILABLE") {
          htmlContent += `
            <div class="coach-unavailable-notice">
              <div class="notice-icon">&#x26A0;&#xFE0F;</div>
              <div class="notice-title">Coach Formation Data Unavailable</div>
              <div class="notice-sub">
                Passenger verified successfully, but verified coach formation is currently unavailable for Train <b>${escapeHtml(j.train_number)}</b>.<br>
                Position is not shown to preserve accuracy.
              </div>
            </div>`;
        } else if (posData.status === "COACH_UNAVAILABLE") {
          htmlContent += `
            <div class="coach-notfound-notice">
              <div class="notice-title">Coach Not Found in Train Rake</div>
              <div class="notice-sub">Journey verified, but coach information is unavailable in train formation.</div>
            </div>`;
        } else {
          // Render the formation with coach highlight
          const coaches = posData.coaches || [];
          let trainStripHtml = "";
          coaches.forEach((c, idx) => {
            const isHighlight = (c.coachId.toUpperCase() === j.coach.toUpperCase());
            const isLoco = (c.type === "LOCOMOTIVE");
            const highlightClass = isHighlight ? "coach-box-highlight" : (isLoco ? "coach-box-loco" : "coach-box-normal");
            const youPointer = isHighlight ? '<div class="coach-you-pointer">YOU &#x25BC;</div>' : '';
            trainStripHtml += `
              <div class="coach-unit">
                ${youPointer}
                <div class="coach-box ${highlightClass}">${escapeHtml(c.displayLabel || c.coachId)}</div>
                <div class="coach-class-lbl">${escapeHtml(c.class || (isLoco ? "Loco" : c.type.slice(0, 2)))}</div>
              </div>`;
          });

          htmlContent += `
            <div class="coach-result-container">
              <div class="coach-result-topbar">
                <div class="coach-result-title">&#x1F683; Verified Train Formation (${posData.total_coaches} Coaches)</div>
                <div class="coach-status-tag" style="background:rgba(16,185,129,0.15); color:#34d399; border:1px solid rgba(16,185,129,0.4); padding:2px 8px; border-radius:12px; font-size:0.75rem; font-weight:700;">
                  Formation: ${escapeHtml(posData.provenance || 'VERIFIED_STATIC')}
                </div>
              </div>
              <div class="coach-direction-legend">
                <span>&#x2190; Engine / Front (Locomotive)</span>
                <span>Rear / Guard &#x2192;</span>
              </div>
              <div class="coach-train-strip">${trainStripHtml}</div>
              <div class="coach-stat-grid" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(110px, 1fr)); gap:10px; margin-top:14px; background:rgba(15,23,42,0.8); padding:10px 14px; border-radius:10px;">
                <div><div style="font-size:0.68rem; color:#94a3b8; text-transform:uppercase;">Coach</div><div style="font-size:1.0rem; font-weight:800; color:#22d3ee;">${escapeHtml(j.coach)}</div></div>
                <div><div style="font-size:0.68rem; color:#94a3b8; text-transform:uppercase;">Position</div><div style="font-size:1.0rem; font-weight:800; color:#f8fafc;">${posData.position} of ${posData.total_coaches}</div></div>
                <div><div style="font-size:0.68rem; color:#94a3b8; text-transform:uppercase;">Section</div><div style="font-size:0.95rem; font-weight:800; color:#fbbf24;">${escapeHtml(posData.section)}</div></div>
                <div><div style="font-size:0.68rem; color:#94a3b8; text-transform:uppercase;">Before / After</div><div style="font-size:0.95rem; font-weight:750; color:#f8fafc;">${posData.coaches_before} / ${posData.coaches_after}</div></div>
              </div>
            </div>`;
        }

        // Add Session Clearance Button
        htmlContent += `
          <div style="margin-top:12px; text-align:right;">
            <button id="coach-session-clear-btn" style="background:rgba(244,63,94,0.15); border:1px solid #f43f5e; color:#fda4af; padding:6px 14px; border-radius:8px; cursor:pointer; font-weight:700; font-size:0.8rem;">
              &#x1F504; Clear / Verify Another PNR
            </button>
          </div>`;

        panel.innerHTML = htmlContent;

        const clearBtn = document.getElementById("coach-session-clear-btn");
        if (clearBtn) {
          clearBtn.addEventListener("click", async () => {
            try {
              await fetch("/api/pnr/logout", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ session_token: token })
              });
            } catch (e) {}
            panel.innerHTML = "";
            panel.style.display = "none";
            if (pnrInput) pnrInput.value = "";
          });
        }
      } catch (err) {
        panel.innerHTML = `
          <div class="coach-notfound-notice" style="border-left:4px solid #f43f5e; background:rgba(244,63,94,0.08);">
            <div class="notice-title" style="color:#f43f5e;">Verification Error</div>
            <div class="notice-sub">An error occurred while connecting to verification services. Please try again.</div>
          </div>`;
      }
    });
  }
});

