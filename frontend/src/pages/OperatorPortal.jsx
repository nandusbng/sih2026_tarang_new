import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

export default function OperatorPortal() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState('');

  useEffect(() => {
    const token = sessionStorage.getItem('token');
    if (!token) {
      navigate('/login');
      return;
    }
    setUserName(sessionStorage.getItem('currentUserName') || 'Operator');
  }, [navigate]);

  return (
    <div className="flex h-screen w-full bg-slate-50 pt-20 overflow-hidden">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col p-4 shrink-0 shadow-sm z-10">
        <div className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-wider mb-4">Workspace</div>
        <button className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-bold bg-teal-600 text-white shadow-sm mb-2">
          <span className="material-symbols-outlined text-[18px]">dashboard</span> Overview
        </button>
        <button className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-mono font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors">
          <span className="material-symbols-outlined text-[18px]">explore</span> Live Missions
        </button>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-y-auto p-8 relative">
        <div className="max-w-6xl mx-auto flex flex-col gap-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-black text-slate-900">Welcome, {userName}</h1>
              <p className="text-slate-500 mt-1">This is a migrated React component view.</p>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col gap-2">
              <span className="material-symbols-outlined text-teal-600 text-3xl">sensors</span>
              <h3 className="font-bold text-slate-900">Live Sonar Telemetry</h3>
              <p className="text-sm text-slate-500">React integration successful.</p>
            </div>
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 flex flex-col gap-2">
              <span className="material-symbols-outlined text-teal-600 text-3xl">map</span>
              <h3 className="font-bold text-slate-900">Tactical Map</h3>
              <p className="text-sm text-slate-500">Awaiting Leaflet integration.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
