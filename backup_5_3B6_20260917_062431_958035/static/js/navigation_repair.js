(function () {
    "use strict";

    function initializeNavigation() {
        const sidebar = document.getElementById("app-sidebar");
        const openButton = document.getElementById("sidebar-open-button");
        const closeButton = document.getElementById("sidebar-close-button");
        const backdrop = document.getElementById("sidebar-backdrop");

        if (!sidebar || !openButton) return;

        function setOpen(isOpen) {
            sidebar.classList.toggle("is-open", isOpen);
            backdrop?.classList.toggle("is-visible", isOpen);
            backdrop?.classList.toggle("is-open", isOpen);
            openButton.setAttribute("aria-expanded", String(isOpen));
            document.body.classList.toggle("navigation-open", isOpen);
        }

        openButton.addEventListener("click", function () {
            setOpen(!sidebar.classList.contains("is-open"));
        });
        closeButton?.addEventListener("click", function () { setOpen(false); });
        backdrop?.addEventListener("click", function () { setOpen(false); });
        sidebar.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", function () {
                if (window.innerWidth <= 992) setOpen(false);
            });
        });
        window.addEventListener("resize", function () {
            if (window.innerWidth > 992) setOpen(false);
        });
        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape") setOpen(false);
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeNavigation);
    } else {
        initializeNavigation();
    }
})();
