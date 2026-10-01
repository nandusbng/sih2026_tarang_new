import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navigation from './components/Navigation';
import Landing from './pages/Landing';
import Login from './pages/Login';
import OperatorPortal from './pages/OperatorPortal';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-ocean-navy text-white font-sans overflow-x-hidden flex flex-col">
        <Navigation />
        <main className="flex-1 flex flex-col relative w-full h-full">
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/login" element={<Login />} />
            <Route path="/operator-portal" element={<OperatorPortal />} />
            {/* Add other routes here as they are migrated */}
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
