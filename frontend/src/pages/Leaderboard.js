/**
 * Leaderboard Page - Ranked student performance view.
 * 
 * Features:
 * - Test selector dropdown
 * - Ranked table: rank, student name, score, accuracy, net_correct, submission time
 * - Top 3 highlighted with gold/silver/bronze badges
 * - Shows only best attempt per student
 */

import React, { useState, useEffect } from 'react';
import { getLeaderboard } from '../services/api';

function Leaderboard() {
    // ── State ─────────────────────────────────────────────────
    const [data, setData] = useState({ tests: [], leaderboard: [], test_id: null });
    const [selectedTest, setSelectedTest] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // ── Initial load - fetch tests and default leaderboard ────
    useEffect(() => {
        const fetchInitial = async () => {
            setLoading(true);
            setError(null);
            try {
                const result = await getLeaderboard();
                setData(result);
                if (result.test_id) {
                    setSelectedTest(result.test_id);
                }
            } catch (err) {
                setError(err.response?.data?.detail || 'Failed to load leaderboard. Is the backend running?');
            } finally {
                setLoading(false);
            }
        };
        fetchInitial();
    }, []);

    // ── Fetch leaderboard when test changes ───────────────────
    const handleTestChange = async (testId) => {
        setSelectedTest(testId);
        setLoading(true);
        setError(null);
        try {
            const result = await getLeaderboard(testId);
            setData(result);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to load leaderboard.');
        } finally {
            setLoading(false);
        }
    };

    // ── Get rank class name ───────────────────────────────────
    const getRankClass = (rank) => {
        if (rank === 1) return 'rank-1';
        if (rank === 2) return 'rank-2';
        if (rank === 3) return 'rank-3';
        return '';
    };

    return (
        <div>
            {/* Page Header */}
            <div className="page-header">
                <h1>Leaderboard</h1>
                <p>Student rankings based on best attempt per test</p>
            </div>

            {/* Test Selector */}
            <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                <div className="form-group" style={{ marginBottom: 0 }}>
                    <label htmlFor="test-selector">Select Test</label>
                    <select
                        id="test-selector"
                        value={selectedTest}
                        onChange={(e) => handleTestChange(e.target.value)}
                    >
                        {data.tests.length === 0 && <option value="">No tests available</option>}
                        {data.tests.map((test) => (
                            <option key={test.id} value={test.id}>
                                {test.name}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Error State */}
            {error && <div className="error-message">{error}</div>}

            {/* Loading State */}
            {loading ? (
                <div className="loading-container">
                    <div className="spinner"></div>
                    <p>Loading leaderboard...</p>
                </div>
            ) : data.leaderboard.length === 0 ? (
                /* Empty State */
                <div className="empty-state">
                    <div className="empty-icon">&#x1F3C6;</div>
                    <h3>No Rankings Available</h3>
                    <p>No scored attempts found for this test. Ingest some assessment data to see rankings.</p>
                </div>
            ) : (
                <>
                    {/* Top 3 Podium Cards */}
                    {data.leaderboard.length >= 3 && (
                        <div className="stats-row" style={{ marginBottom: 'var(--space-lg)' }}>
                            {data.leaderboard.slice(0, 3).map((entry) => (
                                <div key={entry.attempt_id} className="stat-card" style={{
                                    borderLeft: `3px solid ${entry.rank === 1 ? '#eab308' : entry.rank === 2 ? '#94a3b8' : '#d97706'}`
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1 }}>
                                        <span className={`rank-badge ${getRankClass(entry.rank) ? '' : 'default'}`}
                                            style={entry.rank === 1 ? {
                                                background: 'linear-gradient(135deg, #fbbf24, #f59e0b)',
                                                color: '#451a03',
                                                boxShadow: '0 2px 8px rgba(245, 158, 11, 0.3)',
                                                width: 36, height: 36, borderRadius: '50%',
                                                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                                fontWeight: 700, fontSize: '0.875rem'
                                            } : entry.rank === 2 ? {
                                                background: 'linear-gradient(135deg, #cbd5e1, #94a3b8)',
                                                color: '#1e293b',
                                                boxShadow: '0 2px 8px rgba(148, 163, 184, 0.3)',
                                                width: 36, height: 36, borderRadius: '50%',
                                                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                                fontWeight: 700, fontSize: '0.875rem'
                                            } : {
                                                background: 'linear-gradient(135deg, #fdba74, #f97316)',
                                                color: '#431407',
                                                boxShadow: '0 2px 8px rgba(249, 115, 22, 0.3)',
                                                width: 36, height: 36, borderRadius: '50%',
                                                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                                                fontWeight: 700, fontSize: '0.875rem'
                                            }}>
                                            {entry.rank}
                                        </span>
                                        <div>
                                            <div style={{ fontWeight: 600, color: 'var(--text-heading)' }}>
                                                {entry.student.full_name}
                                            </div>
                                            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                                                {entry.student.email || entry.student.phone || '\u2014'}
                                            </div>
                                        </div>
                                    </div>
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{
                                            fontSize: 'var(--font-size-xl)',
                                            fontWeight: 700,
                                            color: entry.rank === 1 ? '#eab308' : 'var(--accent-success)'
                                        }}>
                                            {Number(entry.score).toFixed(1)}
                                        </div>
                                        <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                                            {Number(entry.accuracy).toFixed(1)}% accuracy
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Leaderboard Table */}
                    <div className="table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th>Rank</th>
                                    <th>Student</th>
                                    <th>Score</th>
                                    <th>Accuracy</th>
                                    <th>Net Correct</th>
                                    <th>Correct</th>
                                    <th>Wrong</th>
                                    <th>Skipped</th>
                                    <th>Submitted At</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.leaderboard.map((entry) => (
                                    <tr key={entry.attempt_id} className={`leaderboard-row ${getRankClass(entry.rank)}`}>
                                        <td>
                                            <span className={`rank-badge ${entry.rank > 3 ? 'default' : ''}`}>
                                                {entry.rank}
                                            </span>
                                        </td>
                                        <td>
                                            <div>
                                                <div style={{ fontWeight: 600, color: 'var(--text-heading)' }}>
                                                    {entry.student.full_name}
                                                </div>
                                                <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)', marginTop: 2 }}>
                                                    {entry.student.email || entry.student.phone || '\u2014'}
                                                </div>
                                            </div>
                                        </td>
                                        <td>
                                            <span style={{
                                                fontWeight: 700,
                                                color: entry.is_top_3 ? 'var(--accent-gold)' : 'var(--accent-success)',
                                                fontSize: 'var(--font-size-base)'
                                            }}>
                                                {Number(entry.score).toFixed(1)}
                                            </span>
                                        </td>
                                        <td>{Number(entry.accuracy).toFixed(1)}%</td>
                                        <td>{entry.net_correct}</td>
                                        <td style={{ color: 'var(--accent-success)' }}>{entry.correct}</td>
                                        <td style={{ color: 'var(--accent-danger)' }}>{entry.wrong}</td>
                                        <td style={{ color: 'var(--accent-warning)' }}>{entry.skipped}</td>
                                        <td style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                                            {entry.submitted_at
                                                ? new Date(entry.submitted_at).toLocaleString()
                                                : 'Not submitted'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    );
}

export default Leaderboard;
