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
