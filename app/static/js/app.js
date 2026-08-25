/*
==========================================================
WSBCO Golf Coach
Application JavaScript

File: app/static/js/app.js
Version: 1.0.0
==========================================================
*/

"use strict";

/* ==========================================================
   APPLICATION STARTUP
========================================================== */

document.addEventListener("DOMContentLoaded", () => {

    initializeSidebar();

    initializeTheme();

    initializeAlerts();

    initializeCards();

    initializeForms();

    initializeKeyboardShortcuts();

    console.log("WSBCO Golf Coach v1.0 Loaded");

});


/* ==========================================================
   SIDEBAR
========================================================== */

function initializeSidebar() {

    const sidebar = document.getElementById("app-sidebar");

    const openButton = document.getElementById("sidebar-open-button");

    const closeButton = document.getElementById("sidebar-close-button");

    const backdrop = document.getElementById("sidebar-backdrop");

    if (!sidebar) return;

    function openSidebar() {

        sidebar.classList.add("is-open");

        if (backdrop)
            backdrop.classList.add("is-visible");

        if (openButton)
            openButton.setAttribute(
                "aria-expanded",
                "true"
            );

    }

    function closeSidebar() {

        sidebar.classList.remove("is-open");

        if (backdrop)
            backdrop.classList.remove("is-visible");

        if (openButton)
            openButton.setAttribute(
                "aria-expanded",
                "false"
            );

    }

    if (openButton)
        openButton.addEventListener(
            "click",
            openSidebar
        );

    if (closeButton)
        closeButton.addEventListener(
            "click",
            closeSidebar
        );

    if (backdrop)
        backdrop.addEventListener(
            "click",
            closeSidebar
        );

    window.addEventListener("resize", () => {

        if (window.innerWidth > 1024) {

            closeSidebar();

        }

    });

}


/* ==========================================================
   LIGHT / DARK THEME
========================================================== */

function initializeTheme() {

    const button =
        document.getElementById(
            "theme-toggle-button"
        );

    if (!button) return;

    const savedTheme =
        localStorage.getItem(
            "golfcoach-theme"
        ) || "light";

    applyTheme(savedTheme);

    button.addEventListener("click", () => {

        const current =
            document.documentElement.dataset.theme;

        const next =
            current === "dark"
                ? "light"
                : "dark";

        applyTheme(next);

        localStorage.setItem(
            "golfcoach-theme",
            next
        );

    });

}

function applyTheme(theme) {

    document.documentElement.dataset.theme = theme;

}


/* ==========================================================
   ALERTS
========================================================== */

function initializeAlerts() {

    const alerts =
        document.querySelectorAll(".alert");

    alerts.forEach(alert => {

        setTimeout(() => {

            alert.style.opacity = "0";

            setTimeout(() => {

                alert.remove();

            }, 300);

        }, 5000);

    });

}


/* ==========================================================
   CARD ANIMATION
========================================================== */

function initializeCards() {

    const cards =
        document.querySelectorAll(".card");

    cards.forEach((card, index) => {

        card.style.opacity = "0";

        card.style.transform =
            "translateY(20px)";

        setTimeout(() => {

            card.style.transition =
                "all .35s ease";

            card.style.opacity = "1";

            card.style.transform =
                "translateY(0px)";

        }, index * 80);

    });

}


/* ==========================================================
   FORM HELPERS
========================================================== */

function initializeForms() {

    const forms =
        document.querySelectorAll("form");

    forms.forEach(form => {

        form.addEventListener(
            "submit",
            () => {

                const button =
                    form.querySelector(
                        "button[type='submit']"
                    );

                if (button) {

                    button.disabled = true;

                    button.innerText =
                        "Please Wait...";

                }

            }
        );

    });

}


/* ==========================================================
   TOAST NOTIFICATIONS
========================================================== */

function showToast(
    message,
    type = "success"
) {

    const region =
        document.getElementById(
            "toast-region"
        );

    if (!region) return;

    const toast =
        document.createElement("div");

    toast.className =
        "toast toast-" + type;

    toast.innerText = message;

    region.appendChild(toast);

    setTimeout(() => {

        toast.classList.add("show");

    }, 20);

    setTimeout(() => {

        toast.classList.remove("show");

        setTimeout(() => {

            toast.remove();

        }, 300);

    }, 3500);

}


/* ==========================================================
   DELETE CONFIRMATION
========================================================== */

function confirmDelete(
    message = "Delete this item?"
) {

    return confirm(message);

}


/* ==========================================================
   FETCH WRAPPER
========================================================== */

async function apiRequest(
    url,
    options = {}
) {

    const response =
        await fetch(
            url,
            {
                headers: {
                    "Content-Type":
                        "application/json"
                },
                ...options
            }
        );

    if (!response.ok) {

        throw new Error(
            "HTTP " +
            response.status
        );

    }

    return await response.json();

}


/* ==========================================================
   KEYBOARD SHORTCUTS
========================================================== */

function initializeKeyboardShortcuts() {

    document.addEventListener(
        "keydown",
        function(event) {

            if (
                event.ctrlKey &&
                event.key.toLowerCase() === "h"
            ) {

                event.preventDefault();

                window.location = "/";

            }

            if (
                event.ctrlKey &&
                event.key.toLowerCase() === "s"
            ) {

                event.preventDefault();

                window.location = "/students";

            }

            if (
                event.ctrlKey &&
                event.key.toLowerCase() === "g"
            ) {

                event.preventDefault();

                window.location = "/garmin";

            }

        }
    );

}


/* ==========================================================
   UTILITY FUNCTIONS
========================================================== */

function formatNumber(
    value,
    decimals = 1
) {

    if (
        value === null ||
        value === undefined ||
        isNaN(value)
    ) {

        return "-";

    }

    return Number(value)
        .toFixed(decimals);

}


function formatPercent(value) {

    return formatNumber(value, 1) + "%";

}


function formatDistance(value) {

    return formatNumber(value, 1) + " yd";

}


/* ==========================================================
   END OF FILE
========================================================== */