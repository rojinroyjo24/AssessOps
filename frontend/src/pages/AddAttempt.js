/**
 * AddAttempt Page - Manual form to add a new assessment attempt.
 * 
 * Features:
 * - Student info fields (name, email, phone)
 * - Test info fields (test ID, test name)
 * - Timestamps (started_at, submitted_at)
 * - Answer grid for entering answers per question
 * - Dynamic question count
 * - Submit button that calls the ingestion API
 * - Success/error feedback
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ingestAttempts } from '../services/api';

function AddAttempt() {
    const navigate = useNavigate();

    // ── Form state ────────────────────────────────────────────
    const [form, setForm] = useState({
        event_id: 'evt-manual-' + Date.now(),
        student_name: '',
        student_email: '',
        student_phone: '',
        test_id: '',
        test_name: '',
        started_at: '',
        submitted_at: '',
    });

    const [questionCount, setQuestionCount] = useState(10);
    const [answers, setAnswers] = useState({});
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);

    // ── Handlers ──────────────────────────────────────────────
    const handleFieldChange = (field, value) => {
        setForm(prev => ({ ...prev, [field]: value }));
    };

    const handleAnswerChange = (questionNo, value) => {
        setAnswers(prev => ({ ...prev, [String(questionNo)]: value }));
    };

    const handleQuestionCountChange = (count) => {
        const num = Math.max(1, Math.min(100, parseInt(count) || 1));
        setQuestionCount(num);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setResult(null);

        // Validation
        if (!form.student_name.trim()) {
            setError('Student name is required.');
            setLoading(false);
            return;
        }
        if (!form.student_email.trim() && !form.student_phone.trim()) {
            setError('Either email or phone is required for student identification.');
            setLoading(false);
            return;
        }
        if (!form.test_name.trim()) {
            setError('Test name is required.');
            setLoading(false);
            return;
        }
        if (!form.started_at) {
            setError('Start time is required.');
            setLoading(false);
            return;
        }

        // Build the event payload
        const event = {
            event_id: form.event_id || ('evt-manual-' + Date.now()),
            student_name: form.student_name.trim(),
            student_email: form.student_email.trim() || null,
            student_phone: form.student_phone.trim() || null,
            test_id: form.test_id.trim() || ('test-' + form.test_name.trim().toLowerCase().replace(/\s+/g, '-')),
            test_name: form.test_name.trim(),
            started_at: new Date(form.started_at).toISOString(),
            submitted_at: form.submitted_at ? new Date(form.submitted_at).toISOString() : null,
            answers: answers,
        };

        try {
            const response = await ingestAttempts([event]);
            setResult(response);

            // Reset form on success
            setForm({
                event_id: 'evt-manual-' + Date.now(),
                student_name: '',
                student_email: '',
                student_phone: '',
                test_id: '',
                test_name: '',
                started_at: '',
                submitted_at: '',
            });
            setAnswers({});
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to submit. Is the backend running?');
        } finally {
            setLoading(false);
        }
    };

    // ── Build answer options for a question ───────────────────
    const answerOptions = ['A', 'B', 'C', 'D', 'SKIP'];

    return (
        <div>
            {/* Page Header */}
            <div className="page-header">
                <h1>Add Attempt</h1>
                <p>Manually add a student assessment attempt via the ingestion API</p>
            </div>

            {/* Success Message */}
            {result && (
                <div className="success-message" style={{ marginBottom: 'var(--space-lg)' }}>
                    <div style={{ marginBottom: 'var(--space-sm)', fontWeight: 600 }}>
                        Attempt submitted successfully!
                    </div>
                    <div style={{ fontSize: 'var(--font-size-sm)' }}>
                        Ingested: {result.ingested} | Duplicates: {result.duplicates_detected} | Scored: {result.scored} | Errors: {result.errors}
                    </div>
                    <div style={{ marginTop: 'var(--space-sm)' }}>
                        <button className="btn btn-outline btn-sm" onClick={() => navigate('/')}>
                            View Attempts
                        </button>
                    </div>
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div className="error-message" style={{ marginBottom: 'var(--space-lg)' }}>
                    {error}
                </div>
            )}

            <form onSubmit={handleSubmit}>
                {/* Student Information */}
                <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                    <div className="card-header">
                        <h2>Student Information</h2>
                    </div>
                    <div className="form-grid">
                        <div className="form-group">
                            <label htmlFor="student-name">Full Name *</label>
                            <input
                                id="student-name"
                                type="text"
                                placeholder="e.g. Aarav Sharma"
                                value={form.student_name}
                                onChange={(e) => handleFieldChange('student_name', e.target.value)}
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="student-email">Email</label>
                            <input
                                id="student-email"
                                type="email"
                                placeholder="e.g. aarav@gmail.com"
                                value={form.student_email}
                                onChange={(e) => handleFieldChange('student_email', e.target.value)}
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="student-phone">Phone</label>
                            <input
                                id="student-phone"
                                type="tel"
                                placeholder="e.g. 919876543210"
                                value={form.student_phone}
                                onChange={(e) => handleFieldChange('student_phone', e.target.value)}
                            />
                        </div>
                    </div>
                </div>

                {/* Test Information */}
                <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                    <div className="card-header">
                        <h2>Test Information</h2>
                    </div>
                    <div className="form-grid">
                        <div className="form-group">
                            <label htmlFor="test-name-input">Test Name *</label>
                            <input
                                id="test-name-input"
                                type="text"
                                placeholder="e.g. Physics Mid-Term 2024"
                                value={form.test_name}
                                onChange={(e) => handleFieldChange('test_name', e.target.value)}
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="test-id-input">Test ID (optional)</label>
                            <input
                                id="test-id-input"
                                type="text"
                                placeholder="Auto-generated from test name"
                                value={form.test_id}
                                onChange={(e) => handleFieldChange('test_id', e.target.value)}
                            />
                        </div>
                    </div>
                    <div className="form-grid">
                        <div className="form-group">
                            <label htmlFor="started-at">Started At *</label>
                            <input
                                id="started-at"
                                type="datetime-local"
                                value={form.started_at}
                                onChange={(e) => handleFieldChange('started_at', e.target.value)}
                                required
                            />
                        </div>
                        <div className="form-group">
                            <label htmlFor="submitted-at">Submitted At (optional)</label>
                            <input
                                id="submitted-at"
                                type="datetime-local"
                                value={form.submitted_at}
                                onChange={(e) => handleFieldChange('submitted_at', e.target.value)}
                            />
                        </div>
                    </div>
                </div>

                {/* Answers */}
                <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                    <div className="card-header">
                        <h2>Answers</h2>
                        <div className="form-group" style={{ marginBottom: 0, minWidth: '120px' }}>
                            <label htmlFor="question-count">Questions</label>
                            <input
                                id="question-count"
                                type="number"
                                min="1"
                                max="100"
                                value={questionCount}
                                onChange={(e) => handleQuestionCountChange(e.target.value)}
                                style={{ width: '80px' }}
                            />
                        </div>
                    </div>

                    <div className="answers-grid">
                        {Array.from({ length: questionCount }, (_, i) => i + 1).map((qNo) => (
                            <div key={qNo} className="answer-item">
                                <span className="question-label">Q{qNo}</span>
                                <div className="answer-options">
                                    {answerOptions.map((opt) => (
                                        <button
                                            key={opt}
                                            type="button"
                                            className={`answer-btn ${answers[String(qNo)] === opt ? 'selected' : ''} ${opt === 'SKIP' ? 'skip' : ''}`}
                                            onClick={() => handleAnswerChange(qNo, opt)}
                                        >
                                            {opt}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>

                    <div style={{ marginTop: 'var(--space-md)', display: 'flex', gap: 'var(--space-sm)', flexWrap: 'wrap', alignItems: 'center' }}>
                        <button
                            type="button"
                            className="btn btn-outline btn-sm"
                            onClick={() => {
                                const newAnswers = {};
                                const opts = ['A', 'B', 'C', 'D'];
                                for (let i = 1; i <= questionCount; i++) {
                                    newAnswers[String(i)] = opts[Math.floor(Math.random() * 4)];
                                }
                                setAnswers(newAnswers);
                            }}
                        >
                            Random Fill
                        </button>
                        <button
                            type="button"
                            className="btn btn-outline btn-sm"
                            onClick={() => setAnswers({})}
                        >
                            Clear All
                        </button>
                        <span style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)' }}>
                            {Object.keys(answers).length} / {questionCount} answered
                        </span>
                    </div>
                </div>

                {/* Submit */}
                <div style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'center' }}>
                    <button
                        type="submit"
                        className="btn btn-primary"
                        disabled={loading}
                        style={{ minWidth: '180px' }}
                    >
                        {loading ? 'Submitting...' : 'Submit Attempt'}
                    </button>
                    <button
                        type="button"
                        className="btn btn-outline"
                        onClick={() => navigate('/')}
                    >
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    );
}

export default AddAttempt;
