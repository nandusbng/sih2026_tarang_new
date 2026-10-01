// TARANG Unified Maritime AI Platform - Authoritative Supabase RBAC & Authentication Engine

const ROLE_DESTINATIONS = {
    'survey_operator': 'operator-portal.html',
    'sonar_analyst': 'sonar-analyst.html',
    'marine_portal': 'marine-analyst.html',
    'government_portal': 'gov-authority.html',
    'admin': 'admin-dashboard.html',
    'public': 'public.html'
};

const ROLE_PERMISSIONS = {
    'survey_operator': ['operator-portal.html', 'survey-operator.html', 'sonar-ai.html', 'xtf-upload.html', 'public.html'],
    'sonar_analyst': ['sonar-analyst.html', 'sonar-ai.html', 'operator-portal.html', 'survey-operator.html', 'public.html'],
    'marine_portal': ['marine-analyst.html', 'cleanup-portal.html', 'public.html'],
    'government_portal': ['gov-authority.html', 'operator-portal.html', 'survey-operator.html', 'sonar-analyst.html', 'marine-analyst.html', 'public.html'],
    'admin': ['admin-dashboard.html', 'operator-portal.html', 'survey-operator.html', 'sonar-analyst.html', 'marine-analyst.html', 'cleanup-portal.html', 'gov-authority.html', 'public.html', 'expert-verification.html', 'mission-ops.html', 'logistics.html', 'xtf-upload.html'],
    'public': ['public.html']
};

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

function getCurrentUser() {
    const userRole = sessionStorage.getItem('currentRole');
    const userName = sessionStorage.getItem('currentUserName');
    const instId = sessionStorage.getItem('institutionId') || sessionStorage.getItem('currentUser');
    const token = sessionStorage.getItem('supabaseToken');
    
    if (!userRole || !userName) {
        return null;
    }
    
    return {
        id: instId,
        full_name: userName,
        name: userName,
        role: userRole,
        institution_id: instId,
        email: sessionStorage.getItem('currentUserEmail') || '',
        token: token
    };
}
window.getCurrentUser = getCurrentUser;

const tarangFetch = window.fetch.bind(window);
window.fetch = (input, options = {}) => {
    const url = typeof input === 'string' ? input : input.url;
    const isTarangApi = typeof url === 'string' && url.startsWith('/api/');
    const isAuthApi = typeof url === 'string' && url.startsWith('/api/auth/');
    const token = sessionStorage.getItem('supabaseToken');

    if (!isTarangApi || isAuthApi || !token) {
        return tarangFetch(input, options);
    }

    const headers = new Headers(options.headers || {});
    if (!headers.has('Authorization')) {
        headers.set('Authorization', `Bearer ${token}`);
    }
    return tarangFetch(input, { ...options, headers });
};

async function login(username, password) {
    username = (username || '').trim();
    if (!username || !password) {
        return { success: false, message: 'Please enter your Full Name and password.' };
    }
    
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ full_name: username, password: password })
        });
        
        const data = await response.json().catch(() => ({}));
        
        if (response.ok && data.status === 'success' && data.user) {
            const user = data.user;
            sessionStorage.setItem('currentUser', user.institution_id || user.id);
            const role = normalizeRole(user.role);
            sessionStorage.setItem('currentRole', role);
            sessionStorage.setItem('currentUserName', user.full_name || user.name);
            sessionStorage.setItem('institutionId', user.institution_id || user.id);
            sessionStorage.setItem('currentUserEmail', user.email || '');
            if (data.access_token) {
                sessionStorage.setItem('supabaseToken', data.access_token);
            }
            
            const dest = data.redirect || ROLE_DESTINATIONS[role] || 'operator-portal.html';
            window.location.href = dest;
            return { success: true };
        } else {
            return { 
                success: false, 
                message: data.message || 'Invalid Full Name or password.' 
            };
        }
    } catch (err) {
        console.error('Supabase authentication endpoint failure:', err);
        return { 
            success: false, 
            message: 'Unable to connect to TARANG Supabase Auth service. Please verify network connection.' 
        };
    }
}

async function registerUser(fullName, institutionId, password, confirmPassword, role) {
    fullName = (fullName || '').trim();
    institutionId = (institutionId || '').trim();
    
    if (!fullName) return { success: false, message: 'Please enter your Full Name.' };
    if (!institutionId) return { success: false, message: 'Please enter your Institution ID.' };
    if (!password) return { success: false, message: 'Password is required.' };
    if (!confirmPassword) return { success: false, message: 'Please confirm your password.' };
    if (password !== confirmPassword) return { success: false, message: 'Passwords do not match.' };
    if (!role) return { success: false, message: 'Please select your Team Role.' };

    try {
        const response = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                full_name: fullName,
                institution_id: institutionId,
                password: password,
                confirm_password: confirmPassword,
                role: role
            })
        });
        
        const data = await response.json().catch(() => ({}));
        if (response.ok && data.status === 'success') {
            return { 
                success: true, 
                message: data.message || 'Account registered in Supabase. You can now sign in.',
                redirect: data.redirect 
            };
        } else {
            return { 
                success: false, 
                message: data.message || 'Failed to register user in Supabase.' 
            };
        }
    } catch (err) {
        console.error('Supabase registration error:', err);
        return { 
            success: false, 
            message: 'Registration service unavailable. Check Supabase connection.' 
        };
    }
}

function logout() {
    sessionStorage.clear();
    window.location.href = 'login.html';
}
window.logout = logout;

function protectRoute() {
    const role = sessionStorage.getItem('currentRole');
    const user = sessionStorage.getItem('currentUser');
    
    if (!role || !user) {
        window.location.href = 'login.html?error=unauthorized';
        return;
    }

    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    const allowedPages = ROLE_PERMISSIONS[role] || [];
    if (currentPage !== 'index.html' && currentPage !== 'login.html' && !allowedPages.includes(currentPage)) {
        alert("Access Denied: Your authenticated credentials do not possess clearance for this TARANG portal.");
        window.location.href = ROLE_DESTINATIONS[role] || 'login.html';
    }
}
window.protectRoute = protectRoute;

document.addEventListener('DOMContentLoaded', () => {
    const role = sessionStorage.getItem('currentRole');
    if (!role) return;

    const allowedPages = ROLE_PERMISSIONS[role] || [];
    const navLinks = document.querySelectorAll('nav a');
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && !href.startsWith('#') && !allowedPages.includes(href)) {
            link.style.display = 'none';
        }
    });

    const currentName = sessionStorage.getItem('currentUserName');
    const userDisplay = document.getElementById('user-display-name') || document.getElementById('header-op-name');
    if (userDisplay && currentName) {
        userDisplay.textContent = currentName;
    }
});
