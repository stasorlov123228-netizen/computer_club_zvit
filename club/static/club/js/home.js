(function () {
    const page = document.querySelector('.arena-home');
    const burger = document.querySelector('#burger');
    const nav = document.querySelector('#main-nav');
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const mobileNav = window.matchMedia('(max-width: 850px)');

    if (!page || !burger || !nav) {
        return;
    }

    nav.inert = mobileNav.matches;
    nav.setAttribute('aria-hidden', String(mobileNav.matches));

    function closeMenu() {
        nav.classList.remove('active');
        burger.classList.remove('active');
        burger.setAttribute('aria-expanded', 'false');
        burger.setAttribute('aria-label', 'Відкрити меню');
        nav.inert = mobileNav.matches;
        nav.setAttribute('aria-hidden', String(mobileNav.matches));
    }

    burger.addEventListener('click', function () {
        const isOpen = nav.classList.toggle('active');
        burger.classList.toggle('active', isOpen);
        burger.setAttribute('aria-expanded', String(isOpen));
        nav.inert = mobileNav.matches && !isOpen;
        nav.setAttribute('aria-hidden', String(mobileNav.matches && !isOpen));
        burger.setAttribute(
            'aria-label',
            isOpen ? 'Закрити меню' : 'Відкрити меню'
        );
    });

    nav.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', closeMenu);
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            const wasOpen = burger.getAttribute('aria-expanded') === 'true';
            closeMenu();
            if (wasOpen) {
                burger.focus();
            }
        }
    });

    window.addEventListener('resize', function () {
        if (window.innerWidth > 850) {
            closeMenu();
        }
    });

    if (!reducedMotion.matches && 'IntersectionObserver' in window) {
        const revealItems = page.querySelectorAll('.reveal');
        const observer = new IntersectionObserver(
            function (entries, currentObserver) {
                entries.forEach(function (entry) {
                    if (entry.isIntersecting) {
                        entry.target.classList.add('is-visible');
                        currentObserver.unobserve(entry.target);
                    }
                });
            },
            { threshold: 0.12 }
        );

        page.classList.add('has-motion');
        revealItems.forEach(function (item) {
            observer.observe(item);
        });
    }
})();
