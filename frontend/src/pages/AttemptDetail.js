/**
 * AttemptDetail Page - Detailed view of a single assessment attempt.
 * 
 * Features:
 * - Student and test information cards
 * - Status badge
 * - Score breakdown (correct, wrong, skipped, accuracy, score)
 * - Collapsible raw payload JSON viewer
 * - Duplicate thread showing related attempts
 * - Action buttons: "Recompute Score" and "Flag Attempt"
 * - Flag form with reason textarea
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getAttemptDetail, recomputeScore, flagAttempt } from '../services/api';

function AttemptDetail() {
    const { id } = useParams();
    const navigate = useNavigate();

    // ── State ─────────────────────────────────────────────────
    const [attempt, setAttempt] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showRawPayload, setShowRawPayload] = useState(false);
    const [showAnswers, setShowAnswers] = useState(false);
    const [flagReason, setFlagReason] = useState('');
    const [showFlagForm, setShowFlagForm] = useState(false);
    const [actionMessage, setActionMessage] = useState(null);
    const [actionLoading, setActionLoading] = useState(false);

    // ── Fetch attempt detail ──────────────────────────────────
    useEffect(() => {
        const fetchDetail = async () => {
            setLoading(true);
            setError(null);
            try {
                const data = await getAttemptDetail(id);
                setAttempt(data);
            } catch (err) {
                setError(err.response?.data?.detail || 'Failed to load attempt details.');
            } finally {
                setLoading(false);
            }
        };
        fetchDetail();
    }, [id]);

    // ── Handlers ──────────────────────────────────────────────
    const handleRecompute = async () => {
        setActionLoading(true);
        setActionMessage(null);
        try {
            const result = await recomputeScore(id);
            setActionMessage({ type: 'success', text: `Score recomputed successfully: ${result.score.score}` });
            // Refresh the data
            const data = await getAttemptDetail(id);
            setAttempt(data);
        } catch (err) {
            setActionMessage({
                type: 'error',
                text: err.response?.data?.detail || 'Failed to recompute score.'
            });
        } finally {
            setActionLoading(false);
        }
    };

    const handleFlag = async () => {
        if (!flagReason.trim()) return;
        setActionLoading(true);
        setActionMessage(null);
        try {
            await flagAttempt(id, flagReason.trim());
            setActionMessage({ type: 'success', text: 'Attempt flagged successfully.' });
            setFlagReason('');
            setShowFlagForm(false);
            // Refresh the data
            const data = await getAttemptDetail(id);
            setAttempt(data);
        } catch (err) {
            setActionMessage({
                type: 'error',
                text: err.response?.data?.detail || 'Failed to flag attempt.'
            });
        } finally {
            setActionLoading(false);
        }
    };

    const renderStatusBadge = (status) => {
        const className = `badge badge-${status?.toLowerCase() || 'ingested'}`;
        return <span className={className}>{status || 'UNKNOWN'}</span>;
    };

    // ── Loading / Error States ────────────────────────────────
    if (loading) {
        return (
            <div className="loading-container">
                <div className="spinner"></div>
                <p>Loading attempt details...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div>
                <div className="error-message">{error}</div>
                <button className="btn btn-outline" onClick={() => navigate('/')}>
                    &larr; Back to Attempts
                </button>
            </div>
        );
    }

    if (!attempt) return null;

    return (
        <div>
            {/* Back Navigation */}
            <button
                className="btn btn-ghost"
                onClick={() => navigate('/')}
                style={{ marginBottom: 'var(--space-md)', padding: '6px 0' }}
            >
                &larr; Back to Attempts
            </button>

            {/* Page Header with Status */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 'var(--space-lg)' }}>
                <h1 style={{
                    fontSize: 'var(--font-size-2xl)',
                    fontWeight: 700,
                    color: 'var(--text-heading)',
                    letterSpacing: '-0.02em'
                }}>
                    Attempt Detail
                </h1>
                {renderStatusBadge(attempt.status)}
            </div>

            {/* Action Messages */}
            {actionMessage && (
                <div className={actionMessage.type === 'success' ? 'success-message' : 'error-message'}>
                    {actionMessage.text}
                </div>
            )}

            {/* Action Buttons */}
            <div className="action-buttons">
                <button
                    className="btn btn-primary"
                    onClick={handleRecompute}
                    disabled={actionLoading || attempt.status === 'DEDUPED'}
                >
                    Recompute Score
                </button>
                <button
                    className="btn btn-danger"
                    onClick={() => setShowFlagForm(!showFlagForm)}
                    disabled={actionLoading}
                >
                    Flag Attempt
                </button>
            </div>

            {/* Flag Form */}
            {showFlagForm && (
                <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                    <div className="card-header">
                        <h2>Flag This Attempt</h2>
                    </div>
                    <div className="form-group">
                        <label htmlFor="flag-reason">Reason for flagging</label>
                        <textarea
                            id="flag-reason"
                            value={flagReason}
                            onChange={(e) => setFlagReason(e.target.value)}
                            placeholder="Enter the reason for flagging this attempt..."
                        />
                    </div>
                    <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
                        <button className="btn btn-danger btn-sm" onClick={handleFlag} disabled={!flagReason.trim() || actionLoading}>
                            Submit Flag
                        </button>
                        <button className="btn btn-outline btn-sm" onClick={() => setShowFlagForm(false)}>
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {/* Student & Test Info */}
            <div className="detail-grid">
                {/* Student Information */}
                <div className="card">
                    <div className="card-header">
                        <h2>Student Information</h2>
                    </div>
                    <div className="info-row">
                        <span className="info-label">Name</span>
                        <span className="info-value">{attempt.student?.full_name || '\u2014'}</span>
                    </div>
                    <div className="info-row">
                        <span className="info-label">Email</span>
                        <span className="info-value">{attempt.student?.email || '\u2014'}</span>
                    </div>
                    <div className="info-row">
                        <span className="info-label">Phone</span>
                        <span className="info-value">{attempt.student?.phone || '\u2014'}</span>
                    </div>
                    <div className="info-row">
                        <span className="info-label">Student ID</span>
                        <span className="info-value font-mono" style={{ fontSize: 'var(--font-size-xs)' }}>
                            {attempt.student_id}
                        </span>
                    </div>
                </div>

                {/* Test Information */}
                <div className="card">
                    <div className="card-header">
                        <h2>Test Information</h2>
                    </div>
                    <div className="info-row">
                        <span className="info-label">Test Name</span>
                        <span className="info-value">{attempt.test?.name || '\u2014'}</span>
                    </div>
                    <div className="info-row">
                        <span className="info-label">Max Marks</span>
                        <span className="info-value">{attempt.test?.max_marks || '\u2014'}</span>
                    </div>
                    <div className="info-row">
                        <span className="info-label">Marking Scheme</span>
                        <span className="info-value">
                            +{attempt.test?.negative_marking?.correct || 4} / {attempt.test?.negative_marking?.wrong || -1} / {attempt.test?.negative_marking?.skip || 0}
                        </span>
                    </div>
                    <div className="info-row">
                        <span className="info-label">Started At</span>
                        <span className="info-value">
                            {attempt.started_at ? new Date(attempt.started_at).toLocaleString() : '\u2014'}
                        </span>
                    </div>
                    <div className="info-row">
                        <span className="info-label">Submitted At</span>
                        <span className="info-value">
                            {attempt.submitted_at ? new Date(attempt.submitted_at).toLocaleString() : 'Not submitted (partial)'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Score Breakdown */}
            {attempt.score && (
                <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                    <div className="card-header">
                        <h2>Score Breakdown</h2>
                        <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
                            Computed: {attempt.score.computed_at ? new Date(attempt.score.computed_at).toLocaleString() : '\u2014'}
                        </span>
                    </div>
                    <div className="score-grid">
                        <div className="score-stat highlight">
                            <div className="stat-value">{Number(attempt.score.score).toFixed(1)}</div>
                            <div className="stat-label">Total Score</div>
                        </div>
                        <div className="score-stat correct">
                            <div className="stat-value">{attempt.score.correct}</div>
                            <div className="stat-label">Correct</div>
                        </div>
                        <div className="score-stat wrong">
                            <div className="stat-value">{attempt.score.wrong}</div>
                            <div className="stat-label">Wrong</div>
                        </div>
                        <div className="score-stat skipped">
                            <div className="stat-value">{attempt.score.skipped}</div>
                            <div className="stat-label">Skipped</div>
                        </div>
                        <div className="score-stat">
                            <div className="stat-value">{Number(attempt.score.accuracy).toFixed(1)}%</div>
                            <div className="stat-label">Accuracy</div>
                        </div>
                        <div className="score-stat">
                            <div className="stat-value">{attempt.score.net_correct}</div>
                            <div className="stat-label">Net Correct</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Flags */}
            {attempt.flags && attempt.flags.length > 0 && (
                <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                    <div className="card-header">
                        <h2>Flags ({attempt.flags.length})</h2>
                    </div>
                    {attempt.flags.map((flag) => (
                        <div key={flag.id} className="info-row">
                            <span className="info-label">
                                {flag.created_at ? new Date(flag.created_at).toLocaleString() : '\u2014'}
                            </span>
                            <span className="info-value">{flag.reason}</span>
                        </div>
                    ))}
                </div>
            )}

            {/* Duplicate Thread */}
            {attempt.duplicate_thread && attempt.duplicate_thread.length > 0 && (
                <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                    <div className="card-header">
                        <h2>Duplicate Thread</h2>
                    </div>
                    <div className="duplicate-thread">
                        {attempt.duplicate_thread.map((dup) => (
                            <div key={dup.id} className="duplicate-item">
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <span className="font-mono" style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                                        {dup.id.substring(0, 8)}...
                                    </span>
                                    <span>{dup.student_name || '\u2014'}</span>
                                    {dup.is_canonical && <span className="canonical-badge">CANONICAL</span>}
                                </div>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    {renderStatusBadge(dup.status)}
                                    {dup.score !== null && (
                                        <span style={{ color: 'var(--accent-success)', fontWeight: 700 }}>
                                            {Number(dup.score).toFixed(1)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Answers Viewer */}
            <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                <div
                    className="collapsible-header"
                    onClick={() => setShowAnswers(!showAnswers)}
                >
                    <span>Answers ({Object.keys(attempt.answers || {}).length} questions)</span>
                    <span className={`toggle-icon ${showAnswers ? 'open' : ''}`}>&#x25B6;</span>
                </div>
                {showAnswers && (
                    <div className="json-viewer">
                        {JSON.stringify(attempt.answers, null, 2)}
                    </div>
                )}
            </div>

            {/* Raw Payload Viewer */}
            <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                <div
                    className="collapsible-header"
                    onClick={() => setShowRawPayload(!showRawPayload)}
                >
                    <span>Raw Payload</span>
                    <span className={`toggle-icon ${showRawPayload ? 'open' : ''}`}>&#x25B6;</span>
                </div>
                {showRawPayload && (
                    <div className="json-viewer">
                        {JSON.stringify(attempt.raw_payload, null, 2)}
                    </div>
                )}
            </div>
        </div>
    );
}

export default AttemptDetail;
