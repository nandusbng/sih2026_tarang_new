import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post('/api/auth/login', { username, password });
      sessionStorage.setItem('token', res.data.token);
      sessionStorage.setItem('userRole', res.data.user.role);
      sessionStorage.setItem('currentUserName', res.data.user.username);
      
      const roleMap = {
        'operator': '/operator-portal',
        'sonar_analyst': '/sonar-analyst',
        'marine_analyst': '/marine-analyst',
        'government': '/gov-authority',
        'admin': '/admin'
      };
      navigate(roleMap[res.data.user.role] || '/operator-portal');
    } catch (err) {
      setError('Invalid credentials');
    }
  };

  const devLogin = (roleUser, rolePass) => {
    setUsername(roleUser);
    setPassword(rolePass);
  };

  return (
    <div className="min-h-screen pt-24 pb-12 flex flex-col items-center justify-center bg-slate-50 relative">
      <div className="absolute inset-0 z-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-teal-900/20 via-slate-50 to-slate-50"></div>
      
      <div className="z-10 w-full max-w-md bg-white rounded-2xl shadow-xl border border-slate-200 p-8">
        <div className="flex flex-col items-center mb-8">
          <img src="/logoimage.jpg" className="w-16 h-16 rounded-2xl shadow-md mb-4" alt="Logo" />
          <h2 className="text-2xl font-black text-slate-900">Secure Access</h2>
          <p className="text-sm font-mono text-teal-700 mt-1">TARANG // Authentication</p>
        </div>
        
        {error && <div className="mb-4 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-600 text-xs font-mono text-center">{error}</div>}
        
        <form onSubmit={handleLogin} className="flex flex-col gap-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">USERNAME</label>
            <input type="text" value={username} onChange={e => setUsername(e.target.value)} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-slate-900 focus:outline-none focus:border-teal-500 transition-colors" />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-700 mb-1">PASSWORD</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2.5 text-slate-900 focus:outline-none focus:border-teal-500 transition-colors" />
          </div>
          <button type="submit" className="mt-2 w-full bg-teal-600 hover:bg-teal-700 text-white font-bold py-3 rounded-lg transition-colors flex items-center justify-center gap-2">
            AUTHENTICATE <span className="material-symbols-outlined text-[18px]">lock_open</span>
          </button>
        </form>

        <div className="mt-8 border-t border-slate-200 pt-6">
          <h3 className="text-xs font-mono font-bold text-teal-700 mb-4 text-center">QUICK DEV LOGIN</h3>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'Operator', u: 'op1', p: 'pass' },
              { label: 'Sonar Analyst', u: 'sonar1', p: 'pass' },
              { label: 'Marine Analyst', u: 'marine1', p: 'pass' },
              { label: 'Gov Authority', u: 'gov1', p: 'pass' },
              { label: 'Admin', u: 'admin', p: 'adminpass' },
              { label: 'Public Portal', url: '/public' }
            ].map((btn, i) => (
              btn.url ? (
                <button key={i} onClick={() => navigate(btn.url)} className="p-2 text-left rounded-lg bg-slate-50 border border-slate-200 hover:bg-teal-50/70 hover:border-teal-500/50 transition-all text-xs font-bold text-slate-700">{btn.label}</button>
              ) : (
                <button key={i} onClick={() => devLogin(btn.u, btn.p)} className="p-2 text-left rounded-lg bg-slate-50 border border-slate-200 hover:bg-teal-50/70 hover:border-teal-500/50 transition-all text-xs font-bold text-slate-700">{btn.label}</button>
              )
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
