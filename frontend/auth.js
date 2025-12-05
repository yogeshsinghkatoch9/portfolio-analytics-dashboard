/**
 * Authentication Module for VisionWealth
 * Handles login, register, logout, and token management
 */

const API_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://portfolio-analytics-dashboard-production.up.railway.app';

const Auth = {
    // State
    token: localStorage.getItem('visionwealth_token'),
    user: JSON.parse(localStorage.getItem('visionwealth_user') || 'null'),

    /**
     * Login user
     * @param {string} email 
     * @param {string} password 
     */
    async login(email, password) {
        try {
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Login failed');
            }

            const data = await response.json();
            this.setToken(data.access_token);
            
            // Get user info
            await this.fetchCurrentUser();
            
            return { success: true };
        } catch (error) {
            console.error('Login error:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Register new user
     * @param {string} email 
     * @param {string} password 
     * @param {string} fullName 
     * @param {string} role 
     */
    async register(email, password, fullName, role = 'client') {
        try {
            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    email, 
                    password, 
                    full_name: fullName,
                    role 
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Registration failed');
            }

            return { success: true };
        } catch (error) {
            console.error('Registration error:', error);
            return { success: false, error: error.message };
        }
    },

    /**
     * Get current user info
     */
    async fetchCurrentUser() {
        if (!this.token) return null;

        try {
            const response = await fetch(`${API_URL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                const user = await response.json();
                this.setUser(user);
                return user;
            } else {
                // Token invalid
                this.logout();
                return null;
            }
        } catch (error) {
            console.error('Fetch user error:', error);
            return null;
        }
    },

    /**
     * Logout user
     */
    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('visionwealth_token');
        localStorage.removeItem('visionwealth_user');
        window.location.href = '/login.html';
    },

    /**
     * Set auth token
     */
    setToken(token) {
        this.token = token;
        localStorage.setItem('visionwealth_token', token);
    },

    /**
     * Set user info
     */
    setUser(user) {
        this.user = user;
        localStorage.setItem('visionwealth_user', JSON.stringify(user));
    },

    /**
     * Check if user is authenticated
     */
    isAuthenticated() {
        return !!this.token;
    },

    /**
     * Get auth headers for API requests
     */
    getHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
    },

    /**
     * Initialize auth check on page load
     */
    init() {
        // Check if on protected page without token
        const isPublicPage = window.location.pathname.endsWith('login.html') || 
                             window.location.pathname.endsWith('register.html');
        
        if (!isPublicPage && !this.isAuthenticated()) {
            window.location.href = 'login.html';
        }

        // Redirect to dashboard if on login/register and already authenticated
        if (isPublicPage && this.isAuthenticated()) {
            window.location.href = 'index.html';
        }
    }
};
