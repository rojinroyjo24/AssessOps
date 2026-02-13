/**
 * App.js - Root application component.
 * 
 * Sets up React Router for client-side navigation between:
 * - Attempts List (home page)
 * - Attempt Detail
 * - Leaderboard
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import AttemptsList from './pages/AttemptsList';
import AttemptDetail from './pages/AttemptDetail';
import Leaderboard from './pages/Leaderboard';

function App() {
    return (
        <Router>
            <div className="app-container">
                {/* ── Navigation Bar ─────────────────────────── */}
                <nav className="navbar">
                    <div className="navbar-inner">
                        <div className="navbar-brand">
                            <span className="brand-icon">A</span>
                            <span>AssessOps</span>
                        </div>
                        <div className="navbar-links">
                            <NavLink
                                to="/"
                                end
                                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                            >
                                Attempts
                            </NavLink>
                            <NavLink
                                to="/leaderboard"
                                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                            >
                                Leaderboard
                            </NavLink>
                        </div>
                    </div>
                </nav>

                {/* ── Main Content Area ──────────────────────── */}
                <main className="main-content">
                    <Routes>
                        <Route path="/" element={<AttemptsList />} />
                        <Route path="/attempts/:id" element={<AttemptDetail />} />
                        <Route path="/leaderboard" element={<Leaderboard />} />
                    </Routes>
                </main>

                {/* ── Footer ─────────────────────────────────── */}
                <footer className="app-footer">
                    Assessment Ops Mini Platform &copy; 2024 &mdash; React + FastAPI + PostgreSQL
                </footer>
            </div>
        </Router>
    );
}

export default App;
