/**
 * AttemptsList Page - Displays a filterable, paginated table of all attempts.
 * 
 * Features:
 * - Summary stats cards at top
 * - Table with student name, test name, status badge, score, duplicate count
 * - Filters: test dropdown, status dropdown, has_duplicates checkbox
 * - Search: student name/email/phone
 * - Pagination controls
 * - Click row to navigate to detail page
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAttempts } from '../services/api';

function AttemptsList() {
    // ── State management ──────────────────────────────────────
    const [attempts, setAttempts] = useState([]);
    const [pagination, setPagination] = useState({ page: 1, per_page: 20, total: 0, total_pages: 0 });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Filter state
    const [filters, setFilters] = useState({
        status: '',
        has_duplicates: false,
        search: '',
        page: 1,
        per_page: 20
    });

    const navigate = useNavigate();

    // ── Data fetching ─────────────────────────────────────────
    const fetchAttempts = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            // Build query params, omitting empty values
            const params = {};
            if (filters.status) params.status = filters.status;
            if (filters.has_duplicates) params.has_duplicates = true;
            if (filters.search) params.search = filters.search;
            params.page = filters.page;
            params.per_page = filters.per_page;

            const data = await getAttempts(params);
            setAttempts(data.data || []);
            setPagination(data.pagination || { page: 1, per_page: 20, total: 0, total_pages: 0 });
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to load attempts. Is the backend running?');
            setAttempts([]);
        } finally {
            setLoading(false);
        }
    }, [filters]);

    useEffect(() => {
        fetchAttempts();
    }, [fetchAttempts]);

    // ── Compute summary stats ─────────────────────────────────
    const stats = {
        total: pagination.total,
        scored: attempts.filter(a => a.status === 'SCORED').length,
        deduped: attempts.filter(a => a.status === 'DEDUPED').length,
        flagged: attempts.filter(a => a.status === 'FLAGGED').length,
    };

    // ── Event handlers ────────────────────────────────────────
    const handleFilterChange = (key, value) => {
        setFilters(prev => ({ ...prev, [key]: value, page: 1 }));
    };

    const handlePageChange = (newPage) => {
        setFilters(prev => ({ ...prev, page: newPage }));
    };

    const handleRowClick = (attemptId) => {
        navigate(`/attempts/${attemptId}`);
    };

    // ── Helper to render status badge ─────────────────────────
    const renderStatusBadge = (status) => {
        const className = `badge badge-${status?.toLowerCase() || 'ingested'}`;
        return <span className={className}>{status || 'UNKNOWN'}</span>;
    };

    return (
        <div>
            {/* Page Header */}
            <div className="page-header">
                <h1>Assessment Attempts</h1>
                <p>View and manage student assessment attempts with deduplication and scoring</p>
            </div>

            {/* Summary Stats */}
            <div className="stats-row">
                <div className="stat-card">
                    <div className="stat-card-icon primary">
                        <span role="img" aria-label="total">&#x1F4CB;</span>
                    </div>
                    <div className="stat-card-info">
                        <h3>{stats.total}</h3>
                        <p>Total Attempts</p>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-icon success">
                        <span role="img" aria-label="scored">&#x2705;</span>
                    </div>
                    <div className="stat-card-info">
                        <h3>{stats.scored}</h3>
                        <p>Scored</p>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-icon warning">
                        <span role="img" aria-label="deduped">&#x1F501;</span>
                    </div>
                    <div className="stat-card-info">
                        <h3>{stats.deduped}</h3>
                        <p>Duplicates</p>
                    </div>
                </div>
                <div className="stat-card">
                    <div className="stat-card-icon danger">
                        <span role="img" aria-label="flagged">&#x1F6A9;</span>
                    </div>
                    <div className="stat-card-info">
                        <h3>{stats.flagged}</h3>
                        <p>Flagged</p>
                    </div>
                </div>
            </div>

            {/* Filter Bar */}
            <div className="filter-bar">
                <div className="form-group">
                    <label htmlFor="search-input">Search Student</label>
                    <input
                        id="search-input"
                        type="search"
                        placeholder="Name, email, or phone..."
                        value={filters.search}
                        onChange={(e) => handleFilterChange('search', e.target.value)}
                    />
                </div>

                <div className="form-group">
                    <label htmlFor="status-select">Status</label>
                    <select
                        id="status-select"
                        value={filters.status}
                        onChange={(e) => handleFilterChange('status', e.target.value)}
                    >
                        <option value="">All Statuses</option>
                        <option value="SCORED">Scored</option>
                        <option value="DEDUPED">Deduplicated</option>
                        <option value="INGESTED">Ingested</option>
                        <option value="FLAGGED">Flagged</option>
                    </select>
                </div>

                <div className="form-group">
                    <label>&nbsp;</label>
                    <label className="checkbox-label">
                        <input
                            type="checkbox"
                            checked={filters.has_duplicates}
                            onChange={(e) => handleFilterChange('has_duplicates', e.target.checked)}
                        />
                        Has Duplicates Only
                    </label>
                </div>
            </div>

            {/* Error State */}
            {error && <div className="error-message">{error}</div>}

            {/* Loading State */}
            {loading ? (
                <div className="loading-container">
                    <div className="spinner"></div>
                    <p>Loading attempts...</p>
                </div>
            ) : attempts.length === 0 ? (
                /* Empty State */
                <div className="empty-state">
                    <div className="empty-icon">&#x1F4ED;</div>
                    <h3>No Attempts Found</h3>
                    <p>Try adjusting your filters or ingest some assessment data first.</p>
                </div>
            ) : (
                <>
                    {/* Attempts Table */}
                    <div className="table-wrapper">
                        <table>
                            <thead>
                                <tr>
                                    <th>Student</th>
                                    <th>Test</th>
                                    <th>Status</th>
                                    <th>Score</th>
                                    <th>Accuracy</th>
                                    <th>Started At</th>
                                    <th>Duplicates</th>
                                </tr>
                            </thead>
                            <tbody>
                                {attempts.map((attempt) => (
                                    <tr
                                        key={attempt.id}
                                        className="clickable"
                                        onClick={() => handleRowClick(attempt.id)}
                                    >
                                        <td>
                                            <div>
                                                <div style={{ fontWeight: 600, color: 'var(--text-heading)' }}>
                                                    {attempt.student?.full_name || 'Unknown'}
                                                </div>
                                                <div style={{ color: 'var(--text-muted)', fontSize: 'var(--font-size-xs)', marginTop: 2 }}>
                                                    {attempt.student?.email || attempt.student?.phone || '\u2014'}
                                                </div>
                                            </div>
                                        </td>
                                        <td style={{ color: 'var(--text-secondary)' }}>
                                            {attempt.test?.name || 'Unknown Test'}
                                        </td>
                                        <td>{renderStatusBadge(attempt.status)}</td>
                                        <td>
                                            {attempt.score ? (
                                                <span style={{ fontWeight: 700, color: 'var(--accent-success)' }}>
                                                    {Number(attempt.score.score).toFixed(1)}
                                                </span>
                                            ) : (
                                                <span style={{ color: 'var(--text-muted)' }}>&mdash;</span>
                                            )}
                                        </td>
                                        <td>
                                            {attempt.score ? (
                                                <span style={{ color: 'var(--text-secondary)' }}>
                                                    {Number(attempt.score.accuracy).toFixed(1)}%
                                                </span>
                                            ) : (
                                                <span style={{ color: 'var(--text-muted)' }}>&mdash;</span>
                                            )}
                                        </td>
                                        <td style={{ fontSize: 'var(--font-size-xs)', color: 'var(--text-muted)' }}>
                                            {attempt.started_at
                                                ? new Date(attempt.started_at).toLocaleString()
                                                : '\u2014'}
                                        </td>
                                        <td>
                                            {attempt.duplicate_count > 0 ? (
                                                <span className="badge badge-deduped">{attempt.duplicate_count}</span>
                                            ) : (
                                                <span style={{ color: 'var(--text-muted)' }}>0</span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Pagination */}
                    <div className="pagination">
                        <button
                            className="btn btn-outline btn-sm"
                            disabled={pagination.page <= 1}
                            onClick={() => handlePageChange(pagination.page - 1)}
                        >
                            Previous
                        </button>
                        <span className="pagination-info">
                            Page {pagination.page} of {pagination.total_pages} ({pagination.total} total)
                        </span>
                        <button
                            className="btn btn-outline btn-sm"
                            disabled={pagination.page >= pagination.total_pages}
                            onClick={() => handlePageChange(pagination.page + 1)}
                        >
                            Next
                        </button>
                    </div>
                </>
            )}
        </div>
    );
}

export default AttemptsList;
