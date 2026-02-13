/**
 * API Service - Centralized API client for backend communication.
 * 
 * All API calls go through this service to ensure:
 * - Consistent base URL configuration
 * - Proper error handling
 * - Request/response logging
 */

import axios from 'axios';

// Base URL reads from environment variable, defaults to localhost:8000 for development
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance with default configuration
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 second timeout
});

// ── Log request/response for debugging ─────────────────────
api.interceptors.response.use(
    (response) => {
        // Log the X-Request-ID from response headers for tracing
        const requestId = response.headers['x-request-id'];
        if (requestId) {
            console.debug(`[API] Request ID: ${requestId}`);
        }
        return response;
    },
    (error) => {
        console.error('[API] Request failed:', error.message);
        return Promise.reject(error);
    }
);

/**
 * Fetch paginated list of attempts with optional filters.
 */
export const getAttempts = async (params = {}) => {
    const response = await api.get('/api/attempts', { params });
    return response.data;
};

/**
 * Fetch detailed information for a specific attempt.
 */
export const getAttemptDetail = async (attemptId) => {
    const response = await api.get(`/api/attempts/${attemptId}`);
    return response.data;
};

/**
 * Recompute the score for a specific attempt.
 */
export const recomputeScore = async (attemptId) => {
    const response = await api.post(`/api/attempts/${attemptId}/recompute`);
    return response.data;
};

/**
 * Create a flag on a specific attempt with a reason.
 */
export const flagAttempt = async (attemptId, reason) => {
    const response = await api.post(`/api/attempts/${attemptId}/flag`, { reason });
    return response.data;
};

/**
 * Fetch the leaderboard for a specific test.
 */
export const getLeaderboard = async (testId = null) => {
    const params = testId ? { test_id: testId } : {};
    const response = await api.get('/api/leaderboard', { params });
    return response.data;
};

/**
 * Ingest a batch of attempt events.
 */
export const ingestAttempts = async (events) => {
    const response = await api.post('/api/ingest/attempts', { events });
    return response.data;
};

export default api;
