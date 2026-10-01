// TARANG Role-Based Access Control & Authentication Engine

// Default in-memory fallbacks for offline / static demonstration
const DEFAULT_USERS = {
    'survey_ops': { password: 'tarang2026', role: 'survey_operator', name: 'Cmdr. Rajesh Verma', redirect: 'operator-portal.html' },
    'sonar_expert': { password: 'tarang2026', role: 'sonar_analyst', name: 'Dr. Anya Sharma', redirect: 'sonar-analyst.html' },
    'marine_fleet': { password: 'tarang2026', role: 'marine_analyst', name: 'Capt. Vikram Das', redirect: 'marine-analyst.html' },
    'gov_admin': { password: 'tarang2026', role: 'gov_authority', name: 'Joint Director Alok Roy', redirect: 'gov-authority.html' },
    'platform_admin': { password: 'tarang2026', role: 'platform_admin', name: 'Chief Administrator', redirect: 'admin-dashboard.html' },
    'public': { password: 'public', role: 'public', name: 'Citizen Observer', redirect: 'public.html' }
};

// Map roles to their primary portal destinations
const ROLE_DESTINATIONS = {
    'survey_operator': 'operator-portal.html',
    'sonar_analyst': 'sonar-analyst.html',
    'marine_analyst': 'marine-analyst.html',
    'gov_authority': 'gov-authority.html',
    'platform_admin': 'admin-dashboard.html',
    'public': 'public.html'
};

// Map roles to permitted pages
const ROLE_PERMISSIONS = {
    'survey_operator': ['operator-portal.html', 'survey-operator.html', 'public.html'],
    'sonar_analyst': ['sonar-analyst.html', 'operator-portal.html', 'survey-operator.html', 'public.html'],
    'marine_analyst': ['marine-analyst.html', 'public.html'],
    'gov_authority': ['gov-authority.html', 'operator-portal.html', 'survey-operator.html', 'sonar-analyst.html', 'marine-analyst.html', 'public.html'],
    'platform_admin': ['admin-dashboard.html', 'operator-portal.html', 'survey-operator.html', 'sonar-analyst.html', 'marine-analyst.html', 'gov-authority.html', 'public.html'],
    'public': ['public.html']
};

/**
 * Authenticates user via database backend (/api/auth/login) with fallback to default profiles
 */
async function login(username, password) {
    username = (username || '').trim();
    
    // 1. Try Backend API
    try {
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ institution_id: username, password: password })
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.status === 'success') {
                sessionStorage.setItem('currentUser', data.user.institution_id);
                sessionStorage.setItem('currentRole', data.user.role);
                sessionStorage.setItem('currentUserName', data.user.full_name);
                sessionStorage.setItem('institutionId', data.user.institution_id);
                window.location.href = data.redirect || ROLE_DESTINATIONS[data.user.role] || 'operator-portal.html';
                return { success: true };
            }
        } else {
            const err = await response.json().catch(() => ({}));
            // If explicit invalid credentials response from server, return message
            if (response.status === 401 || response.status === 400) {
                return { success: false, message: err.message || 'Invalid Operator ID or Passcode.' };
            }
        }
    } catch (e) {
        console.warn('Backend /api/auth/login unavailable, checking offline default users:', e);
    }
    
    // 2. Fallback to default in-memory profiles
    const user = DEFAULT_USERS[username.toLowerCase()];
    if (user && user.password === password) {
        sessionStorage.setItem('currentUser', username);
        sessionStorage.setItem('currentRole', user.role);
        sessionStorage.setItem('currentUserName', user.name);
        sessionStorage.setItem('institutionId', username);
        window.location.href = user.redirect;
        return { success: true };
    }
    
    return { success: false, message: 'Invalid Institution ID or Passcode.' };
}

/**
 * Registers new user via database backend (/api/auth/register)
 */
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
            return { success: true, message: data.message || 'Account created successfully.', redirect: data.redirect };
        } else {
            return { success: false, message: data.message || 'Failed to create account.' };
        }
    } catch (e) {
        console.warn('Backend /api/auth/register offline fallback simulation:', e);
        // Offline registration simulation
        sessionStorage.setItem('currentUser', institutionId);
        sessionStorage.setItem('currentRole', role);
        sessionStorage.setItem('currentUserName', fullName);
        sessionStorage.setItem('institutionId', institutionId);
        return { 
            success: true, 
            message: 'Account registered locally (Offline Mode).', 
            redirect: ROLE_DESTINATIONS[role] || 'operator-portal.html' 
        };
    }
}

/**
 * Developer quick login handler for demo testing
 */
function quickDevLogin(roleKey) {
    const roleMapping = {
        'survey_operator': 'survey_ops',
        'sonar_analyst': 'sonar_expert',
        'marine_analyst': 'marine_fleet',
        'gov_authority': 'gov_admin',
        'platform_admin': 'platform_admin',
        'public': 'public'
    };
    
    const userKey = roleMapping[roleKey] || 'survey_ops';
    const profile = DEFAULT_USERS[userKey];
    if (profile) {
        sessionStorage.setItem('currentUser', userKey);
        sessionStorage.setItem('currentRole', profile.role);
        sessionStorage.setItem('currentUserName', profile.name);
        sessionStorage.setItem('institutionId', userKey.toUpperCase());
        window.location.href = profile.redirect;
    }
}

function logout() {
    sessionStorage.clear();
    window.location.href = 'login.html';
}

/**
 * Route protection to enforce role-based access
 */
function protectRoute() {
    const role = sessionStorage.getItem('currentRole');
    
    // If not logged in at all, redirect to login
    if (!role) {
        window.location.href = 'login.html?error=unauthorized';
        return;
    }

    // Get current page filename
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    
    // Check permission
    const allowedPages = ROLE_PERMISSIONS[role] || [];
    if (!allowedPages.includes(currentPage)) {
        alert("Access Denied: You do not have clearance for this TARANG portal.");
        window.location.href = ROLE_DESTINATIONS[role] || 'login.html';
    }
}

// Synchronize portal UI on load
document.addEventListener('DOMContentLoaded', () => {
    const role = sessionStorage.getItem('currentRole');
    if (!role) return;

    const allowedPages = ROLE_PERMISSIONS[role] || [];
    
    // Hide unauthorized nav links
    const navLinks = document.querySelectorAll('nav a');
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && !href.startsWith('#') && !allowedPages.includes(href)) {
            link.style.display = 'none';
        }
    });

    // Populate user name in headers if placeholder elements exist
    const currentName = sessionStorage.getItem('currentUserName');
    const userDisplay = document.getElementById('user-display-name');
    if (userDisplay && currentName) {
        userDisplay.textContent = currentName;
    }
});
