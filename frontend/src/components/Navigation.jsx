import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

export default function Navigation() {
  const [scrolled, setScrolled] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const isPublic = location.pathname === '/' || location.pathname === '/login' || location.pathname === '/public';

  if (!isPublic) return null; // We'll render a specific PortalHeader inside portal views

  return (
    <header className={`fixed top-0 w-full z-50 transition-all duration-300 ${
      scrolled ? 'h-16 bg-[#000f22]/80 backdrop-blur-md border-b border-teal-500/30 shadow-lg' : 'h-20 bg-transparent'
    }`}>
      <div className="max-w-7xl mx-auto h-full px-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/" className="flex items-center gap-3 group">
            <div className={`rounded-full overflow-hidden border border-teal-500/30 bg-white/5 p-0.5 flex items-center justify-center transition-all ${scrolled ? 'w-10 h-10' : 'w-12 h-12'}`}>
              <img src="/logoimage.jpg" className="w-full h-full object-contain rounded-full" alt="TARANG" />
            </div>
            <div className="flex flex-col">
              <span className={`font-black tracking-wider leading-none text-white transition-all ${scrolled ? 'text-lg' : 'text-xl'}`}>TARANG</span>
              <span className="text-[10px] font-mono text-teal-400 tracking-widest uppercase">Marine Intelligence</span>
            </div>
          </Link>
        </div>
        
        <div className="flex items-center gap-6">
          <nav className="hidden md:flex items-center gap-6">
            <Link to="/public" className="text-sm font-mono text-slate-300 hover:text-teal-400 transition-colors">PUBLIC PORTAL</Link>
            <a href="#about" className="text-sm font-mono text-slate-300 hover:text-teal-400 transition-colors">ABOUT</a>
          </nav>
          
          <Link to="/login" className="px-5 py-2 rounded-full bg-teal-600/90 hover:bg-teal-500 text-white font-mono text-xs font-bold transition-all hover:scale-105 hover:shadow-[0_0_15px_rgba(20,184,166,0.5)] flex items-center gap-2">
            <span className="material-symbols-outlined text-[16px]">terminal</span>
            OPERATIONAL ACCESS
          </Link>
        </div>
      </div>
    </header>
  );
}
