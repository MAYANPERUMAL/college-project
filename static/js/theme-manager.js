/**
 * TechMart Theme Manager
 * Supports Light, Dark, and System Preference modes across all portals and roles.
 */

(function () {
    'use strict';

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function getCsrfToken() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        if (input) return input.value;
        return getCookie('csrftoken') || '';
    }

    function resolveTheme(preference) {
        if (preference === 'system') {
            return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
        }
        return preference === 'dark' ? 'dark' : 'light';
    }

    window.setTechMartTheme = function (theme, skipApi) {
        theme = (theme || 'system').toLowerCase();
        if (!['light', 'dark', 'system'].includes(theme)) {
            theme = 'system';
        }

        const effective = resolveTheme(theme);

        // Update DOM attributes
        document.documentElement.setAttribute('data-bs-theme', effective);
        document.documentElement.setAttribute('data-theme-preference', theme);

        // Persist in localStorage
        try {
            localStorage.setItem('techmart_theme_preference', theme);
        } catch (e) {
            console.warn('Unable to access localStorage for theme preference', e);
        }

        // Update UI elements across the page
        updateThemeUI(theme, effective);

        // Synchronize with server if authenticated & not skipped
        if (!skipApi) {
            saveThemeToServer(theme);
        }
    };

    function updateThemeUI(preference, effective) {
        // 1. Update dropdown toggle button icons and labels
        const iconName = preference === 'dark' ? 'dark_mode' : (preference === 'light' ? 'light_mode' : 'brightness_auto');
        const labelText = preference === 'dark' ? 'Dark' : (preference === 'light' ? 'Light' : 'Auto');

        document.querySelectorAll('.theme-current-icon').forEach(function (el) {
            el.textContent = iconName;
        });
        document.querySelectorAll('.theme-current-label').forEach(function (el) {
            el.textContent = labelText;
        });

        // 2. Update checkmarks in dropdown menus
        document.querySelectorAll('.theme-check-icon').forEach(function (el) {
            const target = el.getAttribute('data-theme-target');
            if (target === preference) {
                el.classList.remove('d-none');
            } else {
                el.classList.add('d-none');
            }
        });

        // 3. Update Visual Profile Choice Cards
        document.querySelectorAll('.theme-choice-card').forEach(function (card) {
            const cardTheme = card.getAttribute('data-theme');
            if (cardTheme === preference) {
                card.classList.add('active');
            } else {
                card.classList.remove('active');
            }
        });

        // 4. Update Profile Form Select if present
        document.querySelectorAll('select.theme-preference-select, select[name="theme_preference"]').forEach(function (sel) {
            if (sel.value !== preference) {
                sel.value = preference;
            }
        });
    }

    function saveThemeToServer(theme) {
        const csrfToken = getCsrfToken();
        fetch('/api/update-theme/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ theme: theme })
        })
        .then(function (res) { return res.json(); })
        .then(function (data) {
            // Theme preference saved to server user model
        })
        .catch(function (err) {
            // Fallback: localStorage already maintains the client preference
        });
    }

    // Listen for OS system theme changes in real time
    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function (e) {
            const currentPref = localStorage.getItem('techmart_theme_preference') ||
                document.documentElement.getAttribute('data-theme-preference') || 'system';
            if (currentPref === 'system') {
                const effective = e.matches ? 'dark' : 'light';
                document.documentElement.setAttribute('data-bs-theme', effective);
                updateThemeUI('system', effective);
            }
        });
    }

    // Run on DOM Ready
    document.addEventListener('DOMContentLoaded', function () {
        const storedPref = localStorage.getItem('techmart_theme_preference') ||
            document.documentElement.getAttribute('data-theme-preference') || 'system';
        window.setTechMartTheme(storedPref, true);

        // Bind interactive profile choice cards
        document.querySelectorAll('.theme-choice-card').forEach(function (card) {
            card.addEventListener('click', function () {
                const theme = this.getAttribute('data-theme');
                if (theme) {
                    window.setTechMartTheme(theme);
                }
            });
        });

        // Bind profile select dropdown change
        document.querySelectorAll('select.theme-preference-select, select[name="theme_preference"]').forEach(function (sel) {
            sel.addEventListener('change', function () {
                window.setTechMartTheme(this.value);
            });
        });
    });
})();
