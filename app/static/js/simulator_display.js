(() => {
    const button = document.querySelector('[data-expand-simulator]');
    if (!button) return;

    const preview = button.closest('section');
    let nativeActive = false;
    const fullscreenElement = () => document.fullscreenElement || document.webkitFullscreenElement;

    function setExpanded(expanded) {
        preview.classList.toggle('simulator-expanded', expanded);
        document.body.classList.toggle('simulator-display-expanded', expanded);
        button.textContent = expanded ? 'Exit full screen' : 'Full screen';
        button.setAttribute('aria-pressed', String(expanded));
    }

    function isExpanded() {
        return preview.classList.contains('simulator-expanded');
    }

    async function exitNative() {
        if (fullscreenElement() !== preview) return;
        const exit = document.exitFullscreen || document.webkitExitFullscreen;
        try {
            await exit?.call(document);
        } catch {
            // Safari can leave full screen before the exit request finishes.
        }
    }

    function closePreview() {
        setExpanded(false);
        void exitNative();
        button.focus({preventScroll: true});
    }

    async function openPreview() {
        setExpanded(true);
        const request = preview.requestFullscreen || preview.webkitRequestFullscreen;
        try {
            // Call directly from the tap so Safari can use the user gesture.
            await request?.call(preview);
        } catch {
            // Keep the expanded viewport layout when native full screen is denied.
        }
    }

    function syncFullscreen() {
        if (fullscreenElement() === preview) {
            nativeActive = true;
            if (!isExpanded()) void exitNative();
        } else if (nativeActive) {
            nativeActive = false;
            if (isExpanded()) closePreview();
        }
    }

    button.addEventListener('click', () => {
        if (isExpanded()) closePreview();
        else void openPreview();
    });
    document.addEventListener('fullscreenchange', syncFullscreen);
    document.addEventListener('webkitfullscreenchange', syncFullscreen);
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && isExpanded()) closePreview();
    });
})();
