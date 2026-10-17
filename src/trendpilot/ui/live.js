/* Live bridge. The visual shell stays; research calls the agent. */
(function () {
  const PRESETS = {
    saas: {
      name: "Karatau Materials",
      sector: "building materials yard",
      label: "Materials yard",
      size: "small",
      city: "Taraz",
      offer: "cement, insulation, drywall, and delivery inside the city",
      customer: "small crews and households doing repairs",
      channel: "WhatsApp and a 2GIS card",
      constraint: "thin cash, one truck, cannot stock a new category on a guess",
      competitors: "other building-material yards in Taraz",
    },
    ecom: {
      name: "Satti Med",
      sector: "private outpatient clinic",
      label: "Clinic",
      size: "small",
      city: "Taraz",
      offer: "paid checkups, pediatrics, and basic diagnostics",
      customer: "families who already use Instagram and 2GIS to pick a clinic",
      channel: "Instagram and a 2GIS card",
      constraint: "two doctors, weekday evenings only, no ad budget",
      competitors: "other private clinics listed on 2GIS in Taraz",
    },
    retail: {
      name: "Aksu Route Desk",
      sector: "small tour desk",
      label: "Tour desk",
      size: "micro",
      city: "Taraz",
      offer: "day trips toward Aksu-Zhabagly and the Karatau foothills",
      customer: "visitors and local families booking by phone",
      channel: "Instagram and phone",
      constraint: "two guides, weekends only, no marketplace fees",
      competitors: "other Taraz tour desks and regional park tours",
    },
  };

  const PROMPTS = {
    competitors: "Analyze my competitors from public sources only. Do not invent numbers.",
    opportunities: "Find one local market opportunity I can test without a new ad budget.",
    demand: "Check whether there is local demand for what I already sell.",
    pricing: "Suggest a pricing test I can run on the channel I already own. No ads.",
    risks: "What local risk should I watch, and what should I refuse to do?",
  };

  const STATUS = {
    act: "Test this",
    watch: "Watch",
    not_local: "Not local yet",
    unknown: "Unknown",
    do_nothing: "Do nothing",
  };

  let busy = false;

  function esc(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function state() {
    return window.TrendPilotState;
  }

  function toast(message) {
    const toastEl = document.getElementById("toastNotification");
    const text = document.getElementById("toastText");
    if (!toastEl || !text) return;
    text.textContent = message;
    toastEl.classList.remove("hidden");
    toastEl.classList.add("flex");
    clearTimeout(window.__tpToast);
    window.__tpToast = setTimeout(() => {
      toastEl.classList.add("hidden");
      toastEl.classList.remove("flex");
    }, 2800);
  }

  function company() {
    const s = state();
    const langCode = ((document.getElementById("currentLangCode") || {}).textContent || "EN").trim();
    const language = langCode === "RU" ? "Russian" : langCode === "KK" ? "Kazakh" : "English";
    return {
      name: (s && s.bizName) || "Karatau Materials",
      industry: (s && s.sector) || "local business",
      size: (s && s.size) || "small",
      city: (s && s.city) || "Taraz",
      offer: (s && s.offer) || "",
      customer: (s && s.customer) || "",
      channel: (s && s.channel) || "",
      constraint: (s && s.constraint) || "",
      competitors: (s && s.competitors) || "",
      language,
    };
  }

  function applyCompany(profile) {
    const s = state();
    if (!s) return;
    Object.assign(s, profile);
    s.bizName = profile.name;
    s.sector = profile.sector || profile.industry || "";
    const name = document.getElementById("settingBizName");
    const sector = document.getElementById("settingSector");
    if (name) name.value = profile.name;
    if (sector) {
      let option = [...sector.options].find((item) => item.value === s.sector);
      if (!option) {
        option = new Option(s.sector, s.sector, true, true);
        sector.add(option);
      }
      sector.value = s.sector;
    }
    const context = document.getElementById("topContextName");
    if (context) context.textContent = profile.name;
    const label = document.getElementById("activePresetLabel");
    if (label) label.textContent = profile.label || profile.name || "Company profile";
    const tag = document.getElementById("sidebarBizTag");
    if (tag) tag.textContent = (profile.city || "") + " · " + s.sector;
    fillExtraFields();
    localStorage.setItem("trendpilot-company", JSON.stringify(company()));
  }

  function fillExtraFields() {
    const s = state();
    if (!s) return;
    for (const key of ["city", "offer", "customer", "channel", "constraint", "competitors"]) {
      const input = document.getElementById("setting" + key);
      if (input) input.value = s[key] || "";
    }
  }

  function readExtraFields() {
    const s = state();
    if (!s) return;
    for (const key of ["city", "offer", "customer", "channel", "constraint", "competitors"]) {
      const input = document.getElementById("setting" + key);
      if (input) s[key] = input.value.trim();
    }
  }

  function questionFor(key, custom) {
    const base = custom || PROMPTS[key] || "Find one local, evidenced bet. Search public sources, then file findings.";
    const focus = state()?.focusArea;
    return focus ? `${base}\n\nFocus this research on: ${focus}.` : base;
  }

  function switchToChat() {
    if (window.TrendPilotSwitch) {
      window.TrendPilotSwitch("chat");
      return;
    }
    document.getElementById("viewHero")?.classList.add("hidden");
    document.getElementById("viewChat")?.classList.remove("hidden");
  }

  function shell(userMessage) {
    const profile = company();
    return `
      <div class="flex flex-wrap items-center justify-between gap-2 bg-white/75 backdrop-blur-md px-4 py-2.5 rounded-2xl border border-[#d6e4ee] text-xs text-[#4b6378]">
        <div class="flex items-center gap-2">
          <span class="px-2.5 py-0.5 rounded-full bg-[#dff1f6] text-[#0b7c97] font-semibold">Live research</span>
          <span>Business: <strong class="text-[#0c2033]">${esc(profile.name)}</strong> · ${esc(profile.city)}</span>
        </div>
      </div>
      <div class="flex justify-end animate-fade-up">
        <div class="max-w-[80%] sm:max-w-[65%] rounded-2xl rounded-tr-sm bg-[#0b7c97] text-white px-5 py-3.5 shadow-md">
          <div class="text-[14.5px] leading-relaxed">${esc(userMessage)}</div>
        </div>
      </div>
      <div id="liveProgress" class="inline-flex items-center gap-2.5 px-3.5 py-2 rounded-full bg-white/85 border border-[#d6e4ee] text-xs font-medium text-[#526b80] shadow-sm" role="status" aria-live="polite">
        <span id="liveSpinner" class="w-3.5 h-3.5 rounded-full border-2 border-[#c5e2eb] border-t-[#0b7c97] animate-spin shrink-0" aria-hidden="true"></span>
        <span id="liveStatus">Starting research…</span>
      </div>
      <div id="liveBody"></div>`;
  }

  function setActivity(label, state = "working") {
    const progress = document.getElementById("liveProgress");
    const status = document.getElementById("liveStatus");
    const spinner = document.getElementById("liveSpinner");
    if (status) status.textContent = label;
    if (spinner) spinner.classList.toggle("hidden", state !== "working");
    if (progress) {
      progress.classList.toggle("text-rose-700", state === "error");
      progress.classList.toggle("border-rose-200", state === "error");
      progress.classList.toggle("bg-rose-50", state === "error");
    }
  }

  function activityFor(event) {
    if (event.kind === "search") return "Searching public sources";
    if (event.kind === "fetch") return "Reading a source";
    if (event.kind === "note") return "Reviewing evidence";
    if (event.kind === "findings") return "Putting your findings together";
    if (event.kind === "error") return event.detail || "Research paused";
    if (event.kind === "status" && event.title === "Opening page") return "Opening a source";
    if (event.kind === "status") return "Researching your local market";
    return "Working on your research";
  }

  function addTrace(event) {
    setActivity(activityFor(event), event.kind === "error" ? "error" : "working");
    document.getElementById("viewChat")?.scrollTo({ top: 99999, behavior: "smooth" });
  }

  function renderFindings(findings) {
    const body = document.getElementById("liveBody");
    if (!findings) {
      setActivity("Research finished without findings", "error");
      return;
    }
    setActivity("Research complete", "complete");
    const bets = findings.bets || [];
    const cards = bets.slice(0, 3).map((bet) => `
      <div class="bg-[#f4f9fc] rounded-2xl p-4 border border-[#dfedf5]">
        <div class="text-xs font-medium text-[#5c748a]">${esc(STATUS[bet.status] || bet.status)}</div>
        <div class="text-base font-extrabold text-[#0c2033] mt-1">${esc(bet.title)}</div>
        <div class="text-xs font-semibold text-[#0b7c97] mt-1">${esc(bet.cost || "")}</div>
      </div>`).join("");
    const rows = bets.map((bet) => `
      <tr class="hover:bg-[#f6fafd]">
        <td class="py-3 px-4 font-bold text-[#0c2033]">${esc(bet.title)}</td>
        <td class="py-3 px-4 text-[#3c5368]">${esc(STATUS[bet.status] || bet.status)}</td>
        <td class="py-3 px-4 text-[#3c5368]">${esc(bet.claim)}</td>
        <td class="py-3 px-4 text-[#3c5368]">${esc(bet.test)}</td>
      </tr>`).join("");
    const evidence = bets.flatMap((bet) => bet.evidence || []).map((item) => `
      <a class="block text-xs text-[#0b7c97] hover:underline truncate" href="${esc(item.url)}" target="_blank" rel="noreferrer">${esc(item.what_it_shows || item.url)}</a>`).join("");
    const first = bets[0] || {};
    body.innerHTML = `
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3.5">${cards}</div>
      <div class="overflow-x-auto rounded-2xl border border-[#dfedf5]">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-[#edf5fa] text-[#283f54] text-xs font-bold uppercase tracking-wider">
              <th class="py-3 px-4">Bet</th>
              <th class="py-3 px-4">Status</th>
              <th class="py-3 px-4">Claim</th>
              <th class="py-3 px-4">Test</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-[#edf4f9] text-xs sm:text-[13px] bg-white">${rows}</tbody>
        </table>
      </div>
      <div class="space-y-1">${evidence}</div>
      <div class="bg-gradient-to-r from-[#eaf5f9] via-[#f1f8fc] to-[#eaf5f9] rounded-2xl p-5 border border-[#c5e0ee] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div class="space-y-1">
          <span class="px-2.5 py-0.5 rounded-full bg-[#0b7c97] text-white text-[10.5px] font-bold uppercase tracking-wider">${esc(STATUS[first.status] || "Bet")}</span>
          <h4 class="text-base font-bold text-[#0c2033] pt-1">${esc(first.title || findings.headline)}</h4>
          <p class="text-xs sm:text-[13px] text-[#3a5268] leading-relaxed">${esc(first.kill_line || "")}</p>
        </div>
        <button id="bookmarkInsightBtn" class="shrink-0 px-4 py-2.5 rounded-xl bg-white hover:bg-[#0b7c97] text-[#0b7c97] hover:text-white border border-[#0b7c97]/30 font-semibold text-xs shadow-sm">Save insight</button>
      </div>`;
    document.getElementById("bookmarkInsightBtn")?.addEventListener("click", () => saveInsight(findings, first));
  }

  function saveInsight(findings, bet) {
    const s = state();
    if (!s) return;
    s.savedInsights.unshift({
      id: "ins-" + Date.now(),
      category: "Opportunities",
      title: bet.title || findings.headline,
      metric: STATUS[bet.status] || "Bet",
      body: bet.kill_line || bet.claim || findings.market_read,
      date: "Saved just now",
    });
    const badge = document.getElementById("savedCountBadge");
    if (badge) badge.textContent = String(s.savedInsights.length);
    toast("Saved to your Insights Board");
  }

  function remember(question, findings) {
    const s = state();
    if (!s) return;
    s.historySessions.unshift({
      id: "hist-" + Date.now(),
      title: (findings && findings.headline) || question,
      promptKey: "opportunities",
      category: "Live research",
      date: "Just now",
      summary: (findings && findings.market_read) || question,
      question,
    });
    const badge = document.getElementById("historyCountBadge");
    if (badge) badge.textContent = String(s.historySessions.length);
    const recent = document.getElementById("sidebarRecentList");
    if (recent) {
      document.getElementById("sidebarRecentEmpty")?.classList.add("hidden");
      const button = document.createElement("button");
      button.className = "recent-session-btn w-full text-left px-2.5 py-1.5 rounded-lg text-[12.5px] text-[#496176] hover:bg-[#e4eff6] hover:text-[#0c2033] truncate";
      button.textContent = s.historySessions[0].title;
      button.addEventListener("click", () => window.TrendPilotLive.launch("opportunities", question));
      recent.prepend(button);
    }
  }

  async function launch(key, custom) {
    if (busy) {
      toast("A research run is already going");
      return;
    }
    readExtraFields();
    const question = questionFor(key, custom);
    const container = document.getElementById("chatThreadContainer");
    if (!container) return;
    busy = true;
    switchToChat();
    container.innerHTML = shell(question);
    let findings = null;
    let failure = "";
    try {
      const response = await fetch("/research", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ company: company(), question }),
      });
      if (!response.ok || !response.body) throw new Error("Agent HTTP " + response.status);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (!line.trim()) continue;
          const event = JSON.parse(line);
          if (event.kind === "done") findings = (event.payload || {}).findings || null;
          else if (event.kind === "error") {
            failure = event.detail || event.title || "The agent could not finish.";
            addTrace(event);
          }
          else addTrace(event);
        }
      }
      renderFindings(findings);
      if (!findings && failure) {
        setActivity(failure, "error");
      }
      remember(question, findings);
    } catch (error) {
      setActivity(error.message || "The agent could not finish.", "error");
    } finally {
      busy = false;
    }
  }

  function injectSettings() {
    const modal = document.querySelector("#settingsModal .space-y-4");
    if (!modal || document.getElementById("settingcity")) return;
    const fields = [
      ["city", "City", "Taraz"],
      ["offer", "What they sell", ""],
      ["customer", "Who pays", ""],
      ["channel", "Channel they already own", ""],
      ["constraint", "Hard constraint", ""],
      ["competitors", "Competitors or public URLs", ""],
    ];
    for (const [key, label, placeholder] of fields) {
      const wrap = document.createElement("div");
      wrap.innerHTML = `<label class="block text-xs font-semibold text-[#2c4459] mb-1">${label}</label>
        <input id="setting${key}" type="text" placeholder="${esc(placeholder)}" class="w-full px-3.5 py-2 rounded-xl border border-[#cde0ec] text-sm text-[#0c2033] focus:outline-none focus:border-[#0b7c97]" />`;
      modal.appendChild(wrap);
    }
  }

  function clearDemoMemory() {
    const s = state();
    if (!s) return;
    s.historySessions = [];
    s.savedInsights = [];
    const recent = document.getElementById("sidebarRecentList");
    if (recent) recent.innerHTML = "";
    document.getElementById("sidebarRecentEmpty")?.classList.remove("hidden");
    const history = document.getElementById("historyCountBadge");
    const saved = document.getElementById("savedCountBadge");
    if (history) history.textContent = "0";
    if (saved) saved.textContent = "0";
  }

  function retitlePresets() {
    const labels = {
      saas: "Materials yard · Taraz",
      ecom: "Clinic · Taraz",
      retail: "Tour desk · Taraz",
    };
    document.querySelectorAll(".preset-switch-btn").forEach((button) => {
      const span = button.querySelector("span");
      if (span && labels[button.dataset.preset]) span.textContent = labels[button.dataset.preset];
      button.addEventListener("click", (event) => {
        event.stopImmediatePropagation();
        applyCompany(PRESETS[button.dataset.preset] || PRESETS.saas);
        document.getElementById("profileMenuPopover")?.classList.add("hidden");
        toast("Switched to " + (PRESETS[button.dataset.preset] || PRESETS.saas).name);
      }, true);
    });
  }

  function replaceMic() {
    const unsupportedControls = ["attachBtn", "attachPopover", "attachmentChipsRow", "micBtn", "voiceWaveform"];
    unsupportedControls.forEach((id) => {
      const control = document.getElementById(id);
      if (!control) return;
      control.hidden = true;
      control.classList.add("hidden");
      control.setAttribute("aria-hidden", "true");
    });
  }

  window.TrendPilotLive = { launch };

  window.addEventListener("DOMContentLoaded", () => {
    injectSettings();
    clearDemoMemory();
    retitlePresets();
    replaceMic();
    const saved = localStorage.getItem("trendpilot-company");
    if (saved) {
      try { applyCompany(JSON.parse(saved)); } catch (error) { applyCompany(PRESETS.saas); }
    } else {
      applyCompany(PRESETS.saas);
    }
    const save = document.getElementById("saveSettingsBtn");
    save?.addEventListener("click", () => {
      readExtraFields();
      const s = state();
      if (s) {
        s.bizName = document.getElementById("settingBizName")?.value.trim() || s.bizName;
        s.sector = document.getElementById("settingSector")?.value || s.sector;
      }
      localStorage.setItem("trendpilot-company", JSON.stringify(company()));
    });
  });
})();
