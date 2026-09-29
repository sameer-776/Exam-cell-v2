document.addEventListener("DOMContentLoaded", () => {
  // --- DOM REFERENCES ---
  const mobileNavToggle = document.getElementById("mobileNavToggle");
  const mainNav = document.getElementById("mainNav");

  // Notifications containers
  const deptContainer = document.getElementById("department-notifications-container");
  const commonContainer = document.getElementById("common-notifications-container");
  const guidelinesContainer = document.getElementById("common-guidelines-container");
  const archiveContainer = document.getElementById("archive-notifications-container");
  const resultsCountBadge = document.getElementById("resultsCountBadge");

  // Filter controls
  const searchInput = document.getElementById("search-input");
  const departmentSelect = document.getElementById("department-select");
  const yearSelect = document.getElementById("year-select");
  const categorySelect = document.getElementById("category-select");
  const timeframeSelect = document.getElementById("timeframe-select");
  const btnResetFilters = document.getElementById("btnResetFilters");

  // Pagination controls
  const paginationContainer = document.getElementById("pagination-container");
  const paginationInfo = document.getElementById("paginationInfo");
  const pageIndicator = document.getElementById("pageIndicator");
  const prevPageBtn = document.getElementById("prevPageBtn");
  const nextPageBtn = document.getElementById("nextPageBtn");

  // Preferences controls
  const activePrefsBadge = document.getElementById("activePrefsBadge");
  const btnOpenPrefsModal = document.getElementById("btnOpenPrefsModal");
  const btnClearPrefs = document.getElementById("btnClearPrefs");
  const preferenceModal = document.getElementById("preferenceModal");
  const prefDeptSelect = document.getElementById("prefDeptSelect");
  const prefYearSelect = document.getElementById("prefYearSelect");
  const btnSavePreferences = document.getElementById("btnSavePreferences");
  const btnCancelPrefsModal = document.getElementById("btnCancelPrefsModal");
  const closePrefModalBtn = document.getElementById("closePrefModalBtn");

  // Detail Modal controls
  const detailModalOverlay = document.getElementById("detailModalOverlay");
  const closeDetailModalBtn = document.getElementById("closeDetailModalBtn");
  const modalTitle = document.getElementById("modal-title");
  const modalMeta = document.getElementById("modal-meta");
  const modalBody = document.getElementById("modal-body");
  const modalAttachment = document.getElementById("modal-attachment");
  const modalBadgeWrapper = document.getElementById("modal-badge-wrapper");

  // Calendar controls
  const currentMonthYear = document.getElementById("currentMonthYear");
  const calendarDaysGrid = document.getElementById("calendarDaysGrid");
  const prevMonthBtn = document.getElementById("prevMonthBtn");
  const nextMonthBtn = document.getElementById("nextMonthBtn");
  const todayMonthBtn = document.getElementById("todayMonthBtn");
  const upcomingExamsContainer = document.getElementById("upcomingExamsContainer");
  const calendarFilteredStatus = document.getElementById("calendarFilteredStatus");

  // --- STATE ---
  let currentPage = 1;
  const pageSize = 5;
  let totalPages = 1;
  let searchTimeout = null;
  let lastActiveElement = null;

  // Calendar state
  let currentCalDate = new Date();
  let selectedCalDate = null;
  let allCalendarEvents = [];

  // --- MOBILE NAV TOGGLE ---
  if (mobileNavToggle && mainNav) {
    mobileNavToggle.addEventListener("click", () => {
      mainNav.classList.toggle("active");
    });
    // Close nav when clicking a link
    mainNav.querySelectorAll("a").forEach(link => {
      link.addEventListener("click", () => mainNav.classList.remove("active"));
    });
  }

  // --- WORD WHEEL SETUP ---
  function setupWordWheel() {
    const wordWheel = document.querySelector(".word-wheel");
    const textArray = ["deadlines.", "notifications.", "guidelines.", "results."];
    if (wordWheel && textArray.length > 0) {
      const wordsToDisplay = [...textArray, textArray[0]];
      wordWheel.innerHTML = wordsToDisplay
        .map((word) => `<span class="word-wheel-item">${word}</span>`)
        .join("");
    }
  }

  // --- SKELETON LOADERS ---
  function renderSkeletons(container, count = 3) {
    let skeletons = "";
    for (let i = 0; i < count; i++) {
      skeletons += `
        <div class="skeleton-card" aria-hidden="true">
          <div class="skeleton-line title"></div>
          <div class="skeleton-line meta"></div>
          <div class="skeleton-line"></div>
          <div class="skeleton-line short"></div>
        </div>
      `;
    }
    container.innerHTML = skeletons;
  }

  // --- STUDENT PREFERENCES (LOCALSTORAGE) ---
  const PREFS_STORAGE_KEY = "pu_exam_student_prefs";

  function getStoredPreferences() {
    try {
      const stored = localStorage.getItem(PREFS_STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }

  function setStoredPreferences(prefs) {
    try {
      localStorage.setItem(PREFS_STORAGE_KEY, JSON.stringify(prefs));
    } catch (e) {
      console.error("Failed to save preferences:", e);
    }
  }

  function clearStoredPreferences() {
    try {
      localStorage.removeItem(PREFS_STORAGE_KEY);
    } catch (e) {
      console.error("Failed to clear preferences:", e);
    }
  }

  function applyPreferencesUI() {
    const prefs = getStoredPreferences();
    if (prefs && (prefs.department || prefs.year)) {
      let deptName = prefs.department;
      let yrName = prefs.year;

      if (departmentSelect) {
        const deptOpt = departmentSelect.querySelector(`option[value="${prefs.department}"]`);
        if (deptOpt) deptName = deptOpt.textContent;
        departmentSelect.value = prefs.department || "";
      }
      if (yearSelect) {
        const yrOpt = yearSelect.querySelector(`option[value="${prefs.year}"]`);
        if (yrOpt) yrName = yrOpt.textContent;
        yearSelect.value = prefs.year || "";
      }

      activePrefsBadge.innerHTML = `<i class="fas fa-check-circle" style="color: var(--success);"></i> Personalized: <strong>${deptName || "All Depts"}</strong> (${yrName || "All Years"})`;
      btnClearPrefs.style.display = "inline-flex";
    } else {
      activePrefsBadge.innerHTML = `<i class="fas fa-globe"></i> Browsing: All Departments & Years`;
      btnClearPrefs.style.display = "none";
    }
  }

  // Preference Modal Handlers
  function openPreferenceModal() {
    const prefs = getStoredPreferences() || {};
    if (prefDeptSelect) prefDeptSelect.value = prefs.department || "";
    if (prefYearSelect) prefYearSelect.value = prefs.year || "";
    openModal(preferenceModal, btnOpenPrefsModal);
  }

  function closePreferenceModal() {
    closeModal(preferenceModal);
  }

  if (btnOpenPrefsModal) btnOpenPrefsModal.addEventListener("click", openPreferenceModal);
  if (closePrefModalBtn) closePrefModalBtn.addEventListener("click", closePreferenceModal);
  if (btnCancelPrefsModal) btnCancelPrefsModal.addEventListener("click", closePreferenceModal);

  if (btnSavePreferences) {
    btnSavePreferences.addEventListener("click", () => {
      const dept = prefDeptSelect.value;
      const yr = prefYearSelect.value;
      if (!dept && !yr) {
        clearStoredPreferences();
      } else {
        setStoredPreferences({ department: dept, year: yr });
      }
      applyPreferencesUI();
      closePreferenceModal();
      currentPage = 1;
      fetchNotifications();
      fetchCalendar();
    });
  }

  if (btnClearPrefs) {
    btnClearPrefs.addEventListener("click", () => {
      clearStoredPreferences();
      if (departmentSelect) departmentSelect.value = "";
      if (yearSelect) yearSelect.value = "";
      applyPreferencesUI();
      currentPage = 1;
      fetchNotifications();
      fetchCalendar();
    });
  }

  // --- NOTIFICATIONS FETCH & RENDER ---
  async function fetchNotifications() {
    renderSkeletons(deptContainer, 4);

    const params = new URLSearchParams();
    const dept = departmentSelect.value;
    const year = yearSelect.value;
    const search = searchInput.value.trim();
    const category = categorySelect.value;
    const timeframe = timeframeSelect.value;

    if (dept) params.append("department", dept);
    if (year) params.append("year", year);
    if (search) params.append("search", search);
    if (category && category !== "all") params.append("category", category);
    if (timeframe) params.append("timeframe", timeframe);
    params.append("page", currentPage);
    params.append("limit", pageSize);

    const apiUrl = `/api/notifications?${params.toString()}`;

    try {
      const response = await fetch(apiUrl);
      if (!response.ok) throw new Error("Failed to fetch notifications");
      const data = await response.json();

      // Render side columns always
      renderSideNotifications(guidelinesContainer, data.guidelines, "guideline");
      renderSideNotifications(commonContainer, data.common, "announcement");
      renderArchiveNotifications(archiveContainer, data.archive);

      // Render main filtered list
      renderMainNotifications(deptContainer, data.filtered || data.departmental || [], data.pagination);

      // Urgent popup check
      const allActive = (data.filtered || []).concat(data.departmental || []);
      const urgentPopup = allActive.find((n) => n.is_popup);
      if (urgentPopup && !sessionStorage.getItem(`popup_shown_${urgentPopup.id}`)) {
        sessionStorage.setItem(`popup_shown_${urgentPopup.id}`, "true");
        showPopup(urgentPopup);
      }
    } catch (error) {
      console.error("Error fetching notifications:", error);
      deptContainer.innerHTML = `
        <div class="info-box error">
          <i class="fas fa-exclamation-circle"></i>
          Could not load notifications.
          <button type="button" class="btn btn-secondary" onclick="window.retryFetch()" style="margin-top: 10px; font-size: 0.85rem;">
            <i class="fas fa-redo"></i> Retry
          </button>
        </div>
      `;
      if (paginationContainer) paginationContainer.style.display = "none";
    }
  }
  window.retryFetch = fetchNotifications;

  function renderMainNotifications(container, notifications, pagination) {
    container.innerHTML = "";

    if (!notifications || notifications.length === 0) {
      container.innerHTML = `
        <div class="info-box">
          <i class="fas fa-search"></i> No notifications match your current search and filters.
          <p style="margin: 8px 0 0 0; font-size: 0.85rem; color: var(--muted);">Try changing search terms or clicking "Reset Filters".</p>
        </div>
      `;
      if (paginationContainer) paginationContainer.style.display = "none";
      if (resultsCountBadge) resultsCountBadge.textContent = "0 notices found";
      return;
    }

    if (pagination) {
      totalPages = pagination.total_pages || 1;
      currentPage = pagination.page || 1;
      const total = pagination.total || notifications.length;
      const start = (currentPage - 1) * pageSize + 1;
      const end = Math.min(currentPage * pageSize, total);

      if (resultsCountBadge) resultsCountBadge.textContent = `${total} notice${total === 1 ? '' : 's'}`;
      if (paginationInfo) paginationInfo.textContent = `Showing ${start}-${end} of ${total}`;
      if (pageIndicator) pageIndicator.textContent = `${currentPage} / ${totalPages}`;
      if (prevPageBtn) prevPageBtn.disabled = (currentPage <= 1);
      if (nextPageBtn) nextPageBtn.disabled = (currentPage >= totalPages);
      if (paginationContainer) paginationContainer.style.display = (totalPages > 1) ? "flex" : "none";
    }

    notifications.forEach((notif) => {
      const card = document.createElement("div");
      card.className = `notification-card ${notif.type || "info"}`;

      let attachmentHTML = "";
      if (notif.attachment_url) {
        attachmentHTML = `<a href="${notif.attachment_url}" target="_blank" rel="noopener noreferrer" class="attachment-link">🔗 View Attachment</a>`;
      }

      const postedDate = notif.start_datetime
        ? new Date(notif.start_datetime).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
        : "Recent";

      let urgencyBadge = "";
      if (notif.type === "urgent") urgencyBadge = `<span class="badge-tag urgent"><i class="fas fa-exclamation-triangle"></i> Urgent</span>`;
      else if (notif.type === "upcoming") urgencyBadge = `<span class="badge-tag upcoming"><i class="fas fa-clock"></i> Upcoming</span>`;

      card.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px;">
          <h4>${escapeHTML(notif.title)}</h4>
          ${urgencyBadge}
        </div>
        <div class="meta">
          <span><i class="fas fa-calendar-alt"></i> Posted: ${postedDate}</span>
          ${notif.end_datetime ? `<span><i class="fas fa-hourglass-end"></i> Deadline: ${notif.end_datetime.split('T')[0]}</span>` : ''}
        </div>
        <p>${escapeHTML(notif.body)}</p>
        ${attachmentHTML}
      `;

      card.addEventListener("click", (e) => {
        if (!e.target.closest("a")) showPopup(notif);
      });

      container.appendChild(card);
    });

    observeCards();
  }

  function renderSideNotifications(container, notifications, typeName) {
    container.innerHTML = "";
    if (!notifications || notifications.length === 0) {
      container.innerHTML = `<div class="info-box compact"><i class="fas fa-info-circle"></i> No active ${typeName}s.</div>`;
      return;
    }

    notifications.forEach((notif) => {
      const card = document.createElement("div");
      card.className = `notification-card-side ${notif.type || "info"}`;
      const postedDate = notif.start_datetime
        ? new Date(notif.start_datetime).toLocaleDateString("en-IN", { day: "numeric", month: "short" })
        : "";

      card.innerHTML = `
        <h4>${escapeHTML(notif.title)}</h4>
        <div class="meta">${postedDate}</div>
      `;
      card.addEventListener("click", () => showPopup(notif));
      container.appendChild(card);
    });
  }

  function renderArchiveNotifications(container, notifications) {
    container.innerHTML = "";
    if (!notifications || notifications.length === 0) {
      container.innerHTML = `<div class="info-box compact"><i class="fas fa-archive"></i> Archive is currently empty.</div>`;
      return;
    }

    notifications.forEach((notif) => {
      const card = document.createElement("div");
      card.className = "notification-card archive";
      const postedDate = notif.start_datetime
        ? new Date(notif.start_datetime).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
        : "";

      let attachmentHTML = "";
      if (notif.attachment_url) {
        attachmentHTML = `<a href="${notif.attachment_url}" target="_blank" rel="noopener noreferrer" class="attachment-link">🔗 View Attachment</a>`;
      }

      card.innerHTML = `
        <h4>${escapeHTML(notif.title)}</h4>
        <div class="meta"><span>Archived Notice | Posted: ${postedDate}</span></div>
        <p>${escapeHTML(notif.body)}</p>
        ${attachmentHTML}
      `;
      card.addEventListener("click", (e) => {
        if (!e.target.closest("a")) showPopup(notif);
      });
      container.appendChild(card);
    });
    observeCards();
  }

  // --- EXAMINATION CALENDAR LOGIC ---
  async function fetchCalendar() {
    renderSkeletons(upcomingExamsContainer, 3);
    const dept = departmentSelect ? departmentSelect.value : "";
    const year = yearSelect ? yearSelect.value : "";
    let calUrl = "/api/calendar";
    if (dept || year) {
      calUrl += `?department=${dept}&year=${year}`;
    }

    try {
      const response = await fetch(calUrl);
      if (!response.ok) throw new Error("Failed to fetch calendar");
      allCalendarEvents = await response.json();
      renderCalendarMonthView();
      renderUpcomingExamsList();
    } catch (e) {
      console.error("Error fetching calendar:", e);
      upcomingExamsContainer.innerHTML = `<div class="info-box error"><i class="fas fa-exclamation-circle"></i> Could not load exam calendar.</div>`;
    }
  }

  function renderCalendarMonthView() {
    const year = currentCalDate.getFullYear();
    const month = currentCalDate.getMonth();

    const monthNames = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"
    ];
    if (currentMonthYear) {
      currentMonthYear.textContent = `${monthNames[month]} ${year}`;
    }

    if (!calendarDaysGrid) return;
    calendarDaysGrid.innerHTML = "";

    const firstDayIndex = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const prevMonthDays = new Date(year, month, 0).getDate();

    const today = new Date();
    const isThisMonth = (today.getFullYear() === year && today.getMonth() === month);

    // Group events by day in current month
    const eventsByDay = {};
    allCalendarEvents.forEach(ev => {
      if (ev.date) {
        const [evY, evM, evD] = ev.date.split("-").map(Number);
        if (evY === year && (evM - 1) === month) {
          if (!eventsByDay[evD]) eventsByDay[evD] = [];
          eventsByDay[evD].push(ev);
        }
      }
    });

    // Previous month filler days
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const cell = document.createElement("div");
      cell.className = "calendar-day-cell other-month";
      cell.textContent = prevMonthDays - i;
      calendarDaysGrid.appendChild(cell);
    }

    // Current month days
    for (let day = 1; day <= daysInMonth; day++) {
      const cell = document.createElement("div");
      cell.className = "calendar-day-cell";
      cell.textContent = day;

      const dateStr = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;

      if (isThisMonth && today.getDate() === day) {
        cell.classList.add("today");
      }

      if (selectedCalDate === dateStr) {
        cell.classList.add("selected");
      }

      const dayEvents = eventsByDay[day];
      if (dayEvents && dayEvents.length > 0) {
        cell.classList.add("has-exam");
        const dotsWrap = document.createElement("div");
        dotsWrap.className = "exam-dots";
        dayEvents.slice(0, 3).forEach(ev => {
          const dot = document.createElement("span");
          dot.className = `exam-dot ${ev.exam_type || "other"}`;
          dotsWrap.appendChild(dot);
        });
        cell.appendChild(dotsWrap);
      }

      cell.addEventListener("click", () => {
        if (selectedCalDate === dateStr) {
          selectedCalDate = null;
        } else {
          selectedCalDate = dateStr;
        }
        renderCalendarMonthView();
        renderUpcomingExamsList();
      });

      calendarDaysGrid.appendChild(cell);
    }

    // Trailing filler days for 7-column grid
    const totalCells = firstDayIndex + daysInMonth;
    const remaining = (7 - (totalCells % 7)) % 7;
    for (let j = 1; j <= remaining; j++) {
      const cell = document.createElement("div");
      cell.className = "calendar-day-cell other-month";
      cell.textContent = j;
      calendarDaysGrid.appendChild(cell);
    }
  }

  function renderUpcomingExamsList() {
    if (!upcomingExamsContainer) return;
    upcomingExamsContainer.innerHTML = "";

    let eventsToShow = allCalendarEvents;

    if (selectedCalDate) {
      eventsToShow = allCalendarEvents.filter(ev => ev.date === selectedCalDate);
      if (calendarFilteredStatus) {
        calendarFilteredStatus.textContent = `Filtered to ${selectedCalDate}`;
      }
    } else {
      if (calendarFilteredStatus) {
        calendarFilteredStatus.textContent = "Showing upcoming";
      }
    }

    if (!eventsToShow || eventsToShow.length === 0) {
      upcomingExamsContainer.innerHTML = `
        <div class="info-box compact">
          <i class="fas fa-calendar-check"></i> No examinations scheduled ${selectedCalDate ? "on this date." : "for your selection."}
        </div>
      `;
      return;
    }

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    eventsToShow.forEach(ev => {
      const card = document.createElement("div");
      card.className = `upcoming-exam-card ${ev.exam_type || "other"}`;

      let countdownText = "";
      let countdownClass = "countdown-badge";

      if (ev.date) {
        const [ey, em, ed] = ev.date.split("-").map(Number);
        const examDate = new Date(ey, em - 1, ed);
        const diffDays = Math.ceil((examDate - today) / (1000 * 60 * 60 * 24));

        if (diffDays < 0) {
          countdownText = "Completed";
        } else if (diffDays === 0) {
          countdownText = "Today!";
          countdownClass += " today";
        } else if (diffDays === 1) {
          countdownText = "Tomorrow";
        } else if (diffDays <= 7) {
          countdownText = `In ${diffDays} days`;
        } else if (diffDays <= 30) {
          const weeks = Math.round(diffDays / 7);
          countdownText = `In ${weeks} week${weeks > 1 ? 's' : ''}`;
        } else {
          countdownText = `${ev.date}`;
        }
      }

      const formattedDate = ev.date
        ? new Date(ev.date).toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", year: "numeric" })
        : "Date TBA";

      card.innerHTML = `
        <div class="exam-card-header">
          <h4>${escapeHTML(ev.title)}</h4>
          <span class="${countdownClass}">${countdownText}</span>
        </div>
        <div class="exam-meta-row">
          <span><i class="fas fa-calendar-day"></i> ${formattedDate}</span>
          ${ev.time_session ? `<span><i class="fas fa-clock"></i> ${escapeHTML(ev.time_session)}</span>` : ""}
          ${ev.venue ? `<span><i class="fas fa-map-marker-alt"></i> ${escapeHTML(ev.venue)}</span>` : ""}
        </div>
        ${ev.description ? `<p class="exam-description">${escapeHTML(ev.description)}</p>` : ""}
      `;

      upcomingExamsContainer.appendChild(card);
    });
  }

  // Calendar month buttons
  if (prevMonthBtn) {
    prevMonthBtn.addEventListener("click", () => {
      currentCalDate.setMonth(currentCalDate.getMonth() - 1);
      renderCalendarMonthView();
    });
  }
  if (nextMonthBtn) {
    nextMonthBtn.addEventListener("click", () => {
      currentCalDate.setMonth(currentCalDate.getMonth() + 1);
      renderCalendarMonthView();
    });
  }
  if (todayMonthBtn) {
    todayMonthBtn.addEventListener("click", () => {
      currentCalDate = new Date();
      selectedCalDate = null;
      renderCalendarMonthView();
      renderUpcomingExamsList();
    });
  }

  // --- DETAIL MODAL & POPUP ---
  function showPopup(notif) {
    if (!detailModalOverlay) return;

    modalTitle.textContent = notif.title || "Notification Details";
    modalBody.innerHTML = escapeHTML(notif.body || "No further details available.").replace(/\n/g, "<br>");

    const postedDate = notif.start_datetime
      ? new Date(notif.start_datetime).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" })
      : "";

    modalMeta.textContent = postedDate ? `Posted on ${postedDate}` : "";

    let badgeHtml = `<span class="badge-tag ${notif.type}">${notif.type}</span>`;
    if (notif.is_popup) badgeHtml += ` <span class="badge-tag urgent">Urgent Alert</span>`;
    modalBadgeWrapper.innerHTML = badgeHtml;

    if (notif.attachment_url) {
      modalAttachment.innerHTML = `<a href="${notif.attachment_url}" target="_blank" rel="noopener noreferrer" class="attachment-link">🔗 View Attached Document</a>`;
    } else {
      modalAttachment.innerHTML = "";
    }

    openModal(detailModalOverlay);
  }

  function hidePopup() {
    closeModal(detailModalOverlay);
  }

  if (closeDetailModalBtn) closeDetailModalBtn.addEventListener("click", hidePopup);

  // --- ACCESSIBLE MODAL HELPERS ---
  function openModal(modalEl, triggerEl) {
    lastActiveElement = triggerEl || document.activeElement;
    modalEl.classList.add("active");
    const focusable = modalEl.querySelector("button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])");
    if (focusable) focusable.focus();
  }

  function closeModal(modalEl) {
    modalEl.classList.remove("active");
    if (lastActiveElement && typeof lastActiveElement.focus === "function") {
      lastActiveElement.focus();
    }
  }

  // Escape key closes open modals
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      if (preferenceModal && preferenceModal.classList.contains("active")) {
        closePreferenceModal();
      }
      if (detailModalOverlay && detailModalOverlay.classList.contains("active")) {
        hidePopup();
      }
    }
  });

  // Clicking overlay backdrop closes modal
  window.addEventListener("click", (e) => {
    if (e.target === detailModalOverlay) hidePopup();
    if (e.target === preferenceModal) closePreferenceModal();
  });

  // --- FILTER & PAGINATION LISTENERS ---
  function handleFilterChange() {
    currentPage = 1;
    fetchNotifications();
    fetchCalendar();
  }

  if (departmentSelect) departmentSelect.addEventListener("change", handleFilterChange);
  if (yearSelect) yearSelect.addEventListener("change", handleFilterChange);
  if (categorySelect) categorySelect.addEventListener("change", handleFilterChange);
  if (timeframeSelect) timeframeSelect.addEventListener("change", handleFilterChange);

  if (searchInput) {
    searchInput.addEventListener("input", () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        currentPage = 1;
        fetchNotifications();
      }, 350);
    });
  }

  if (btnResetFilters) {
    btnResetFilters.addEventListener("click", () => {
      searchInput.value = "";
      categorySelect.value = "all";
      timeframeSelect.value = "";
      departmentSelect.value = "";
      yearSelect.value = "";
      clearStoredPreferences();
      applyPreferencesUI();
      currentPage = 1;
      fetchNotifications();
      fetchCalendar();
    });
  }

  if (prevPageBtn) {
    prevPageBtn.addEventListener("click", () => {
      if (currentPage > 1) {
        currentPage--;
        fetchNotifications();
        document.getElementById("notifications").scrollIntoView({ behavior: "smooth" });
      }
    });
  }

  if (nextPageBtn) {
    nextPageBtn.addEventListener("click", () => {
      if (currentPage < totalPages) {
        currentPage++;
        fetchNotifications();
        document.getElementById("notifications").scrollIntoView({ behavior: "smooth" });
      }
    });
  }

  // --- CARD ANIMATION OBSERVER ---
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.08 }
  );

  function observeCards() {
    document
      .querySelectorAll(".notification-card:not(.visible)")
      .forEach((card) => observer.observe(card));
  }

  function escapeHTML(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // --- INITIALIZATION ---
  setupWordWheel();
  applyPreferencesUI();
  fetchNotifications();
  fetchCalendar();

  const yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = new Date().getFullYear();
});
