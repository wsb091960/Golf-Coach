(() => {
    const button = document.querySelector('[data-expand-simulator]');
    if (!button) return;

    const preview = button.closest('section');
    function setExpanded(expanded) {
        preview.classList.toggle('simulator-expanded', expanded);
        document.body.classList.toggle('simulator-display-expanded', expanded);
        button.textContent = expanded ? 'Exit full screen' : 'Full screen';
        button.setAttribute('aria-pressed', String(expanded));
        button.focus({preventScroll: true});
    }

    button.addEventListener('click', () => {
        setExpanded(!preview.classList.contains('simulator-expanded'));
    });
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && preview.classList.contains('simulator-expanded')) {
            setExpanded(false);
        }
    });
})();
