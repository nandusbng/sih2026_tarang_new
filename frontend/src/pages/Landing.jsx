import React from 'react';
import { Link } from 'react-router-dom';

export default function Landing() {
  return (
    <div className="relative min-h-screen w-full overflow-hidden flex flex-col justify-center bg-black">
      {/* Background Video */}
      <video 
        autoPlay 
        loop 
        muted 
        playsInline 
        className="absolute top-0 left-0 w-full h-full object-cover z-0 opacity-80 mix-blend-screen"
      >
        <source src="/LandingPage.mp4" type="video/mp4" />
      </video>

      {/* Gradient Overlay */}
      <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-r from-[#000f22]/90 via-[#000f22]/60 to-transparent z-10"></div>

      {/* Hero Content */}
      <div className="relative z-20 max-w-7xl mx-auto px-6 w-full pt-20">
        <div className="max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-teal-500/10 border border-teal-500/20 mb-6">
            <span className="w-2 h-2 rounded-full bg-teal-400 animate-pulse"></span>
            <span className="text-xs font-mono text-teal-400 tracking-wider">SYSTEM ACTIVE V2.4</span>
          </div>
          
          <h1 className="text-5xl md:text-7xl font-black tracking-tight text-white mb-6 leading-[1.1]">
            Next-Gen Marine<br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-teal-400 to-emerald-300">
              Intelligence
            </span>
          </h1>
          
          <p className="text-slate-300 text-lg mb-10 max-w-xl font-light leading-relaxed">
            AI-driven sonar analysis and autonomous drone swarm coordination for marine debris detection, UXO clearance, and tactical waterway management.
          </p>

          <div className="flex flex-col sm:flex-row items-center gap-4">
            <Link to="/login" className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-teal-600 hover:bg-teal-500 text-white font-mono text-sm font-bold transition-all shadow-[0_0_20px_rgba(20,184,166,0.3)] hover:shadow-[0_0_30px_rgba(20,184,166,0.6)] flex items-center justify-center gap-2">
              <span className="material-symbols-outlined">rocket_launch</span>
              INITIALIZE PORTAL
            </Link>
            <Link to="/public" className="w-full sm:w-auto px-8 py-3.5 rounded-xl bg-white/5 hover:bg-white/10 text-white font-mono text-sm font-bold transition-all border border-white/10 flex items-center justify-center gap-2">
              PUBLIC DASHBOARD
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
