(function () {
    "use strict";

    function createButton(sidebar) {
        const button = document.createElement("button");
        button.id = "sidebar-open-button";
        button.className = "icon-button universal-menu-button";
        button.type = "button";
        button.setAttribute("aria-label", "Open navigation");
        button.setAttribute("aria-controls", sidebar.id);
        button.setAttribute("aria-expanded", "false");
        button.innerHTML = '<span aria-hidden="true">☰</span>';
        document.body.appendChild(button);
        return button;
    }

    function createCloseButton(sidebar) {
        const button = document.createElement("button");
        button.className = "universal-sidebar-close";
        button.type = "button";
        button.setAttribute("aria-label", "Close navigation");
        button.innerHTML = '<span aria-hidden="true">×</span>';
        sidebar.appendChild(button);
        return button;
    }

    function createBackdrop() {
        const backdrop = document.createElement("div");
        backdrop.id = "sidebar-backdrop";
        backdrop.className = "sidebar-backdrop";
        document.body.appendChild(backdrop);
        return backdrop;
    }

    function initializeNavigation() {
        const sidebar = document.getElementById("app-sidebar") || document.querySelector("aside.sidebar");
        if (!sidebar) return;
        if (!sidebar.id) sidebar.id = "app-sidebar";

        const openButton = document.getElementById("sidebar-open-button") || createButton(sidebar);
        const closeButton = document.getElementById("sidebar-close-button") || createCloseButton(sidebar);
        const backdrop = document.getElementById("sidebar-backdrop") || createBackdrop();

        function setOpen(isOpen) {
            sidebar.classList.toggle("is-open", isOpen);
            backdrop.classList.toggle("is-visible", isOpen);
            backdrop.classList.toggle("is-open", isOpen);
            openButton.setAttribute("aria-expanded", String(isOpen));
            document.body.classList.toggle("navigation-open", isOpen);
        }

        /* Capture phase makes this work even when an older page script stops
           propagation on the same control. */
        openButton.addEventListener("click", function (event) {
            event.preventDefault();
            event.stopImmediatePropagation();
            setOpen(!sidebar.classList.contains("is-open"));
        }, true);
        closeButton.addEventListener("click", function () { setOpen(false); });
        backdrop.addEventListener("click", function () { setOpen(false); });
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
