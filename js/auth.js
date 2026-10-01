// TARANG authentication, routing, and signed demo-session support.
// This file is the sole browser-side authority for the six portal IDs.

const ROLE_DESTINATIONS = Object.freeze({
    survey_operator: 'operator-portal.html',
    sonar_analyst: 'sonar-analyst.html',
    marine_portal: 'marine-analyst.html',
    government_portal: 'gov-authority.html',
    admin: 'admin-dashboard.html',
    public: 'public.html'
});

const DEMO_PORTAL_DESTINATIONS = ROLE_DESTINATIONS;

const ROLE_PERMISSIONS = Object.freeze({
    survey_operator: ['operator-portal.html', 'survey-operator.html', 'sonar-ai.html', 'xtf-upload.html', 'public.html'],
    sonar_analyst: ['sonar-analyst.html', 'sonar-ai.html', 'operator-portal.html', 'survey-operator.html', 'public.html'],
    marine_portal: ['marine-analyst.html', 'cleanup-portal.html', 'public.html'],
    government_portal: ['gov-authority.html', 'operator-portal.html', 'survey-operator.html', 'sonar-analyst.html', 'marine-analyst.html', 'public.html'],
    admin: ['admin-dashboard.html', 'operator-portal.html', 'survey-operator.html', 'sonar-analyst.html', 'marine-analyst.html', 'cleanup-portal.html', 'gov-authority.html', 'public.html', 'expert-verification.html', 'mission-ops.html', 'logistics.html', 'xtf-upload.html'],
    public: ['public.html']
});

const PROTECTED_PAGES = new Set([
    'operator-portal.html', 'survey-operator.html', 'sonar-analyst.html',
    'sonar-ai.html', 'marine-analyst.html', 'gov-authority.html',
    'cleanup-portal.html', 'admin-dashboard.html', 'expert-verification.html', 'mission-ops.html',
    'logistics.html', 'xtf-upload.html'
]);

const SESSION_KEYS = [
    'currentUser', 'currentRole', 'currentUserName', 'institutionId',
    'currentUserEmail', 'supabaseToken', 'tarangSessionMode',
    'tarangSessionExpiresAt'
];
const REMEMBERED_SESSION_KEY = 'tarangRememberedSession';

function normalizeRole(role) {
    const aliases = {
        marine_analyst: 'marine_portal',
        gov_authority: 'government_portal',
        platform_admin: 'admin',
        sonar_operator: 'sonar_analyst',
        sonar_expert: 'sonar_analyst',
        atmiya: 'admin'
    };
    const value = String(role || '').trim().toLowerCase();
    return aliases[value] || value;
}

function clearTarangSession({ preserveRemembered = false } = {}) {
    SESSION_KEYS.forEach(key => sessionStorage.removeItem(key));
    if (!preserveRemembered) localStorage.removeItem(REMEMBERED_SESSION_KEY);
}

function readStoredSession() {
    const role = normalizeRole(sessionStorage.getItem('currentRole'));
    const userName = sessionStorage.getItem('currentUserName');
    const expiresAt = Number(sessionStorage.getItem('tarangSessionExpiresAt') || 0);
    if (expiresAt && Date.now() >= expiresAt) {
        clearTarangSession();
        return null;
    }
    if (!role || !userName || !ROLE_DESTINATIONS[role]) return null;
    return {
        id: sessionStorage.getItem('institutionId') || sessionStorage.getItem('currentUser'),
        institution_id: sessionStorage.getItem('institutionId') || sessionStorage.getItem('currentUser'),
        full_name: userName,
        name: userName,
        role,
        email: sessionStorage.getItem('currentUserEmail') || '',
        token: sessionStorage.getItem('supabaseToken') || '',
        mode: sessionStorage.getItem('tarangSessionMode') || 'authenticated',
        expires_at: expiresAt || null
    };
}

function restoreRememberedSession() {
    if (sessionStorage.getItem('currentRole')) return;
    try {
        const remembered = JSON.parse(localStorage.getItem(REMEMBERED_SESSION_KEY) || 'null');
        if (!remembered || !remembered.values || (remembered.expiresAt && Date.now() >= remembered.expiresAt)) {
            localStorage.removeItem(REMEMBERED_SESSION_KEY);
            return;
        }
        Object.entries(remembered.values).forEach(([key, value]) => {
            if (SESSION_KEYS.includes(key) && value !== null && value !== undefined) {
                sessionStorage.setItem(key, String(value));
            }
        });
    } catch (error) {
        console.warn('Unable to restore the remembered TARANG session.', error);
        localStorage.removeItem(REMEMBERED_SESSION_KEY);
    }
}

function establishSession(data, { mode = 'authenticated', remember = false } = {}) {
    const user = data && data.user;
    const role = normalizeRole(user && user.role);
    if (!user || !role || !ROLE_DESTINATIONS[role] || !data.access_token) {
        throw new Error('The authentication response did not contain a valid TARANG session.');
    }

    clearTarangSession({ preserveRemembered: true });
    const expiresAt = data.expires_in ? Date.now() + Number(data.expires_in) * 1000 : 0;
    const values = {
        currentUser: user.institution_id || user.id,
        currentRole: role,
        currentUserName: user.full_name || user.name || 'TARANG User',
        institutionId: user.institution_id || user.id,
        currentUserEmail: user.email || '',
        supabaseToken: data.access_token,
        tarangSessionMode: mode,
        tarangSessionExpiresAt: expiresAt || ''
    };
    Object.entries(values).forEach(([key, value]) => sessionStorage.setItem(key, String(value)));

    if (remember && mode === 'authenticated') {
        localStorage.setItem(REMEMBERED_SESSION_KEY, JSON.stringify({ values, expiresAt }));
    } else if (mode === 'demo') {
        // A demo deliberately ends with the browser session and is never
        // restored after its signed expiry window.
        localStorage.removeItem(REMEMBERED_SESSION_KEY);
    }
    return { ...user, role };
}

/** Returns the active browser session, or null if it has expired. */
function getCurrentUser() {
    restoreRememberedSession();
    return readStoredSession();
}
window.getCurrentUser = getCurrentUser;

// Add the token to protected TARANG API calls. Auth endpoints deliberately
// stay token-free because they establish a new session themselves.
const nativeFetch = window.fetch.bind(window);
window.fetch = (input, options = {}) => {
    const url = typeof input === 'string' ? input : input.url;
    const isTarangApi = typeof url === 'string' && url.startsWith('/api/');
    const isAuthApi = typeof url === 'string' && url.startsWith('/api/auth/');
    const token = sessionStorage.getItem('supabaseToken');
    if (!isTarangApi || isAuthApi || !token) return nativeFetch(input, options);

    const headers = new Headers(options.headers || {});
    if (!headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);
    return nativeFetch(input, { ...options, headers });
};

async function parseJson(response) {
    const data = await response.json().catch(() => ({}));
    return data && typeof data === 'object' ? data : {};
}

async function login(fullName, password, { remember = false } = {}) {
    if (!(fullName || '').trim() || !password) {
        return { success: false, message: 'Please enter your Full Name and password.' };
    }
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: fullName.trim(), password })
        });
        const data = await parseJson(response);
        if (!response.ok || data.status !== 'success') {
            return { success: false, message: data.message || 'Invalid Full Name or password.' };
        }
        const user = establishSession(data, { mode: 'authenticated', remember });
        window.location.assign(data.redirect || ROLE_DESTINATIONS[user.role]);
        return { success: true };
    } catch (error) {
        console.error('TARANG sign-in failed:', error);
        return { success: false, message: 'Authentication service is unavailable. Start TARANG through its Flask server and try again.' };
    }
}
window.login = login;

async function startDemoPortal(portalKey) {
    const portal = normalizeRole(portalKey);
    if (!DEMO_PORTAL_DESTINATIONS[portal]) {
        return { success: false, message: 'Please choose one of the six TARANG demo portals.' };
    }
    try {
        const response = await fetch('/api/auth/demo-access', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ portal })
        });
        const data = await parseJson(response);
        if (!response.ok || data.status !== 'success') {
            return { success: false, message: data.message || 'Demo session could not be created.' };
        }
        const user = establishSession(data, { mode: 'demo' });
        window.location.assign(data.redirect || DEMO_PORTAL_DESTINATIONS[user.role]);
        return { success: true };
    } catch (error) {
        console.error('TARANG demo-session request failed:', error);
        return { success: false, message: 'Demo session could not be created: TARANG server connection is unavailable.' };
    }
}
window.startDemoPortal = startDemoPortal;

async function registerUser(fullName, institutionId, password) {
    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: fullName.trim(), institution_id: institutionId.trim(), password })
        });
        const data = await parseJson(response);
        return response.ok && data.status === 'success'
            ? { success: true, message: data.message }
            : { success: false, message: data.message || 'Unable to submit the access request.' };
    } catch (error) {
        console.error('TARANG access-request submission failed:', error);
        return { success: false, message: 'Access request could not be stored: TARANG server connection is unavailable.' };
    }
}
window.registerUser = registerUser;

function logout() {
    clearTarangSession();
    window.location.assign('login.html');
}
window.logout = logout;

function protectRoute() {
    const user = getCurrentUser();
    if (!user) {
        window.location.replace('login.html?error=unauthorized');
        return false;
    }
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const allowedPages = ROLE_PERMISSIONS[user.role] || [];
    if (PROTECTED_PAGES.has(currentPage) && !allowedPages.includes(currentPage)) {
        console.warn(`Blocked ${user.role} from ${currentPage}.`);
        window.location.replace(ROLE_DESTINATIONS[user.role] || 'login.html');
        return false;
    }
    return true;
}
window.protectRoute = protectRoute;

function synchronisePortalChrome() {
    const user = getCurrentUser();
    if (!user) return;
    const allowedPages = ROLE_PERMISSIONS[user.role] || [];
    document.querySelectorAll('nav a').forEach(link => {
        const href = (link.getAttribute('href') || '').split('?')[0];
        if (href && !href.startsWith('#') && href.endsWith('.html') && !allowedPages.includes(href)) {
            link.style.display = 'none';
        }
    });
    const userDisplay = document.getElementById('user-display-name') || document.getElementById('header-op-name');
    if (userDisplay) userDisplay.textContent = user.full_name;
}

function installExitControl() {
    const page = window.location.pathname.split('/').pop();
    const user = getCurrentUser();
    if (!user || !PROTECTED_PAGES.has(page) || document.getElementById('tarang-session-exit')) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.id = 'tarang-session-exit';
    button.textContent = user.mode === 'demo' ? 'Exit Demo' : 'Logout';
    button.title = 'End this TARANG session';
    button.style.cssText = 'position:fixed;right:18px;bottom:18px;z-index:9999;border:1px solid #0f766e;background:#042f2e;color:#ecfeff;border-radius:999px;padding:10px 14px;font:700 12px Inter,Arial,sans-serif;box-shadow:0 8px 24px rgba(2,44,34,.28);cursor:pointer;';
    button.addEventListener('click', logout);
    document.body.appendChild(button);
}

document.addEventListener('DOMContentLoaded', () => {
    restoreRememberedSession();
    const page = window.location.pathname.split('/').pop() || 'index.html';
    if (PROTECTED_PAGES.has(page) && !protectRoute()) return;
    synchronisePortalChrome();
    installExitControl();
});
