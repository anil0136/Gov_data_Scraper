document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.querySelector("#dashboardSearch");
    const cards = Array.from(document.querySelectorAll(".record-card"));
    const sections = Array.from(document.querySelectorAll(".data-section"));
    const chips = Array.from(document.querySelectorAll("[data-section-filter]"));
    const status = document.querySelector("#resultStatus");

    let activeSection = "all";

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

    chips.forEach((chip) => {
        chip.addEventListener("click", () => {
            activeSection = chip.dataset.sectionFilter;
            chips.forEach((item) => item.classList.toggle("is-active", item === chip));
            applyFilters();
        });
    });

    if (searchInput) {
        searchInput.addEventListener("input", applyFilters);
    }

    applyFilters();
});
