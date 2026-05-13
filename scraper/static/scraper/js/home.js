document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.querySelector("#dashboardSearch");
    const sections = Array.from(document.querySelectorAll(".data-section"));
    const chips = Array.from(document.querySelectorAll("[data-section-filter]"));
    const status = document.querySelector("#resultStatus");

    let activeSection = "all";

    function escapeHtml(value) {
        return String(value || "").replace(/[&<>"']/g, (char) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            "\"": "&quot;",
            "'": "&#39;",
        }[char]));
    }

    function createCard(item) {
        const card = document.createElement("article");
        card.className = "record-card";
        card.dataset.search = item.search_text || "";

        const media = item.image_url
            ? `<div class="record-media"><img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.title)}" loading="lazy" onerror="this.parentElement.style.display='none';"></div>`
            : "";
        const description = item.description ? `<p>${escapeHtml(item.description)}</p>` : "";
        const meta = Array.isArray(item.meta) && item.meta.length
            ? `<div class="meta">${item.meta.map((entry) => `<span class="pill">${escapeHtml(entry.label)}: ${escapeHtml(entry.value)}</span>`).join("")}</div>`
            : "";
        const source = item.url
            ? `<a class="source-link" href="${escapeHtml(item.url)}" target="_blank" rel="noopener">Open source</a>`
            : "";

        card.innerHTML = `
            ${media}
            <div class="record-main">
                <h3>${escapeHtml(item.title)}</h3>
                ${description}
            </div>
            ${meta}
            ${source}
        `;
        return card;
    }

    function updateSectionCounts(section) {
        const cleanCount = Number(section.dataset.cleanCount || "0");
        const checkedCount = Number(section.dataset.checkedCount || "0");
        const totalCount = Number(section.dataset.totalCount || "0");
        const countBox = section.querySelector(".section-counts");
        if (!countBox) {
            return;
        }

        const strong = countBox.querySelector("strong");
        const label = countBox.querySelector("span");
        if (strong) {
            strong.textContent = cleanCount;
        }
        if (label) {
            label.textContent = `shown from ${checkedCount} checked / ${totalCount} saved`;
        }
    }

    function applyFilters() {
        const query = searchInput ? searchInput.value.trim().toLowerCase() : "";
        let visibleCards = 0;

        sections.forEach((section) => {
            const sectionName = section.dataset.section;
            const sectionAllowed = activeSection === "all" || activeSection === sectionName;
            let visibleInSection = 0;

            section.querySelectorAll(".record-card").forEach((card) => {
                const searchable = (card.dataset.search || "").toLowerCase();
                const cardAllowed = sectionAllowed && (query === "" || searchable.includes(query));
                card.classList.toggle("is-hidden", !cardAllowed);

                if (cardAllowed) {
                    visibleCards += 1;
                    visibleInSection += 1;
                }
            });

            section.classList.toggle("is-hidden", !sectionAllowed || visibleInSection === 0);
        });

        if (status) {
            status.textContent = `${visibleCards} records visible`;
        }
    }

    async function loadRemainingSectionRecords(section) {
        const grid = section.querySelector("[data-record-grid]");
        const loadStatus = section.querySelector("[data-load-status]");
        const emptyState = section.querySelector("[data-empty-state]");
        const kind = section.dataset.kind;
        const totalCount = Number(section.dataset.totalCount || "0");
        let offset = Number(section.dataset.nextOffset || "0");

        if (!grid || !kind || offset >= totalCount) {
            if (loadStatus) {
                loadStatus.remove();
            }
            return;
        }

        while (offset < totalCount) {
            try {
                const response = await fetch(`/api/dashboard/${encodeURIComponent(kind)}/?offset=${offset}&limit=250`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                const payload = await response.json();

                payload.items.forEach((item) => {
                    grid.appendChild(createCard(item));
                });

                const cleanCount = Number(section.dataset.cleanCount || "0") + payload.clean_count;
                const checkedCount = Number(section.dataset.checkedCount || "0") + payload.checked_count;
                section.dataset.cleanCount = String(cleanCount);
                section.dataset.checkedCount = String(checkedCount);
                section.dataset.nextOffset = String(payload.next_offset);
                offset = payload.next_offset;

                if (emptyState && cleanCount > 0) {
                    emptyState.classList.add("is-hidden");
                }
                updateSectionCounts(section);
                applyFilters();

                if (payload.done || payload.checked_count === 0) {
                    break;
                }
            } catch (error) {
                if (loadStatus) {
                    loadStatus.textContent = "Some records could not be loaded. Refresh to retry.";
                }
                return;
            }

            await new Promise((resolve) => setTimeout(resolve, 20));
        }

        if (loadStatus) {
            loadStatus.textContent = "All clean records loaded.";
        }
    }

    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            activeSection = chip.dataset.sectionFilter;
            chips.forEach((item) => item.classList.toggle("is-active", item === chip));
            applyFilters();

            const target = sections.find((section) => section.dataset.section === activeSection);
            const scrollTarget = activeSection === "all" ? document.querySelector(".dashboard") : target;
            if (scrollTarget && !scrollTarget.classList.contains("is-hidden")) {
                requestAnimationFrame(() => {
                    const sectionHead = scrollTarget.querySelector(".section-head");
                    const targetElement = sectionHead || scrollTarget;
                    const targetTop = targetElement.getBoundingClientRect().top + window.scrollY - 12;
                    window.scrollTo({
                        top: Math.max(targetTop, 0),
                        behavior: "smooth",
                    });
                });
            }
        });
    });

    if (searchInput) {
        searchInput.addEventListener("input", applyFilters);
    }

    applyFilters();
    sections.forEach((section) => {
        loadRemainingSectionRecords(section);
    });
});
