import React, { useState } from 'react';

const PORTALS = [
  { key: 'survey_operator', label: 'Survey Operator', description: 'Field Survey Workspace', redirect: 'operator-portal.html' },
  { key: 'sonar_analyst', label: 'Sonar Analyst', description: 'Acoustic Review Desk', redirect: 'sonar-analyst.html' },
  { key: 'marine_portal', label: 'Marine Portal', description: 'Response & Clearance', redirect: 'marine-analyst.html' },
  { key: 'government_portal', label: 'Government Portal', description: 'Governance Overview', redirect: 'gov-authority.html' },
  { key: 'admin', label: 'Admin', description: 'Platform Administration', redirect: 'admin-dashboard.html' },
  { key: 'public', label: 'Public Portal', description: 'Ocean Awareness Platform', redirect: 'public.html' },
];

async function readResponse(response) {
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.status !== 'success') {
    throw new Error(data.message || 'The TARANG service could not complete the request.');
  }
  return data;
}

function establishSession(data, mode = 'authenticated') {
  const user = data.user || {};
  sessionStorage.setItem('currentUser', user.institution_id || user.id || 'tarang-user');
  sessionStorage.setItem('currentRole', user.role || 'survey_operator');
  sessionStorage.setItem('currentUserName', user.full_name || user.name || 'TARANG User');
  sessionStorage.setItem('institutionId', user.institution_id || user.id || '');
  sessionStorage.setItem('currentUserEmail', user.email || '');
  sessionStorage.setItem('supabaseToken', data.access_token || '');
  sessionStorage.setItem('tarangSessionMode', mode);
  if (data.expires_in) {
    sessionStorage.setItem('tarangSessionExpiresAt', String(Date.now() + Number(data.expires_in) * 1000));
  }
}

export default function Login() {
  const [view, setView] = useState('signin');
  const [fullName, setFullName] = useState('');
  const [institutionId, setInstitutionId] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const redirect = (destination) => window.location.assign(destination);

  const handleSignIn = async (event) => {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      const data = await readResponse(await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: fullName.trim(), password }),
      }));
      establishSession(data);
      if (remember) localStorage.setItem('tarangRememberedSession', 'true');
      redirect(data.redirect || 'operator-portal.html');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };

  const handleRequestAccess = async (event) => {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    try {
      const data = await readResponse(await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name: fullName.trim(), institution_id: institutionId.trim(), password }),
      }));
      setMessage(data.message || 'Access account created. You can now sign in.');
      setView('signin');
    } catch (error) {
      setMessage(error.message);
    } finally {
      setBusy(false);
    }
  };

  const launchDemo = async (portal) => {
    setBusy(true);
    setMessage('Opening the selected TARANG demo workspace…');
    try {
      const data = await readResponse(await fetch('/api/auth/demo-access', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ portal: portal.key }),
      }));
      establishSession(data, 'demo');
      redirect(data.redirect || portal.redirect);
    } catch (error) {
      setMessage(error.message);
      setBusy(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 p-6 flex items-center justify-center">
      <section className="w-full max-w-2xl rounded-2xl bg-white border border-slate-200 shadow-xl p-8">
        <header className="text-center mb-7">
          <img src="/logoimage.jpg" className="w-16 h-16 rounded-full mx-auto mb-3" alt="TARANG logo" />
          <h1 className="text-3xl font-black text-slate-900">TARANG</h1>
          <p className="text-xs font-mono uppercase tracking-wider text-teal-700">Unified Maritime AI Platform</p>
        </header>

        {message && <div className="mb-5 rounded-lg border border-teal-200 bg-teal-50 p-3 text-sm text-teal-800">{message}</div>}

        <div className="flex rounded-lg bg-slate-100 p-1 mb-6">
          <button type="button" onClick={() => setView('signin')} className={`flex-1 rounded-md py-2 font-bold ${view === 'signin' ? 'bg-teal-600 text-white' : 'text-slate-600'}`}>Sign In</button>
          <button type="button" onClick={() => setView('request')} className={`flex-1 rounded-md py-2 font-bold ${view === 'request' ? 'bg-teal-600 text-white' : 'text-slate-600'}`}>Request Access</button>
        </div>

        <form onSubmit={view === 'signin' ? handleSignIn : handleRequestAccess} className="space-y-4">
          <label className="block text-sm font-semibold text-slate-700">Full Name
            <input required value={fullName} onChange={(event) => setFullName(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
          </label>
          {view === 'request' && <label className="block text-sm font-semibold text-slate-700">Institution ID
            <input required value={institutionId} onChange={(event) => setInstitutionId(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
          </label>}
          <label className="block text-sm font-semibold text-slate-700">Password
            <input required minLength={view === 'request' ? 8 : undefined} type="password" value={password} onChange={(event) => setPassword(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2" />
          </label>
          {view === 'signin' && <label className="flex items-center gap-2 text-sm text-slate-700"><input type="checkbox" checked={remember} onChange={(event) => setRemember(event.target.checked)} /> Remember this terminal device</label>}
          <button disabled={busy} className="w-full rounded-lg bg-teal-600 py-3 font-bold text-white disabled:opacity-60">{busy ? 'Working…' : view === 'signin' ? 'Authenticate & Enter Portal' : 'Request Access'}</button>
        </form>

        <section className="mt-8 border-t border-slate-200 pt-6">
          <h2 className="font-bold text-slate-900">Authenticated / Enter Portal</h2>
          <p className="mt-1 text-sm text-slate-500">Choose a workspace to start a temporary demo session and enter directly.</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            {PORTALS.map((portal) => <button key={portal.key} type="button" disabled={busy} onClick={() => launchDemo(portal)} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-left hover:border-teal-400 disabled:opacity-60"><span className="block font-bold text-slate-900">{portal.label}</span><span className="text-xs text-slate-500">{portal.description}</span></button>)}
          </div>
          <button type="button" disabled={busy} onClick={() => launchDemo(PORTALS[0])} className="mt-4 w-full rounded-lg bg-slate-900 py-3 font-bold text-white disabled:opacity-60">One-Click Demo</button>
        </section>
        <a className="mt-5 block text-center text-sm font-semibold text-teal-700 hover:underline" href="public.html">Explore the Ocean Awareness →</a>
      </section>
    </main>
  );
}
