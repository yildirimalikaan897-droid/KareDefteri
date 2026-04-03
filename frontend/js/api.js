// ========== KareDefteri API Service ==========

const API_BASE = '/api';

class ApiService {
    constructor() {
        this.token = localStorage.getItem('token');
    }

    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem('token', token);
        } else {
            localStorage.removeItem('token');
        }
    }

    getToken() {
        return this.token;
    }

    async request(endpoint, options = {}) {
        const url = `${API_BASE}${endpoint}`;
        const headers = { ...options.headers };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        if (!(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers,
            });

            const data = await response.json();

            if (!response.ok) {
                throw { status: response.status, ...data };
            }

            return data;
        } catch (err) {
            if (err.status) throw err;
            throw { error: 'Bağlantı hatası. Lütfen tekrar deneyin.' };
        }
    }

    // Auth
    async register(data) {
        return this.request('/auth/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async verifyEmail(email, code) {
        return this.request('/auth/verify', {
            method: 'POST',
            body: JSON.stringify({ email, code })
        });
    }

    async login(login, password) {
        return this.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ login, password })
        });
    }

    async resendCode(email) {
        return this.request('/auth/resend-code', {
            method: 'POST',
            body: JSON.stringify({ email })
        });
    }

    async getMe() {
        return this.request('/auth/me');
    }

    // Users
    async searchUsers(q) {
        return this.request(`/users/search?q=${encodeURIComponent(q)}`);
    }

    async getUser(id) {
        return this.request(`/users/${id}`);
    }

    async getUserPosts(id, page = 1) {
        return this.request(`/users/${id}/posts?page=${page}`);
    }

    async getFollowers(id) {
        return this.request(`/users/${id}/followers`);
    }

    async getFollowing(id) {
        return this.request(`/users/${id}/following`);
    }

    async follow(id) {
        return this.request(`/users/${id}/follow`, { method: 'POST' });
    }

    async unfollow(id) {
        return this.request(`/users/${id}/follow`, { method: 'DELETE' });
    }

    // Posts
    async createPost(formData) {
        return this.request('/posts', {
            method: 'POST',
            body: formData,
            headers: { 'Authorization': `Bearer ${this.token}` }
        });
    }

    async getPost(id) {
        return this.request(`/posts/${id}`);
    }

    async deletePost(id) {
        return this.request(`/posts/${id}`, { method: 'DELETE' });
    }

    // Feed
    async getFeed(page = 1) {
        return this.request(`/feed?page=${page}`);
    }

    // Reactions
    async reactPost(id, reaction) {
        return this.request(`/posts/${id}/react`, {
            method: 'POST',
            body: JSON.stringify({ reaction })
        });
    }

    // Reports
    async reportPost(id, reason) {
        return this.request(`/posts/${id}/report`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        });
    }

    // Stories
    async createStory(formData) {
        return this.request('/stories', {
            method: 'POST',
            body: formData,
            headers: { 'Authorization': `Bearer ${this.token}` }
        });
    }

    async getStoriesFeed() {
        return this.request('/stories/feed');
    }

    async viewStory(id) {
        return this.request(`/stories/${id}/view`, { method: 'POST' });
    }

    // Admin
    async getAdminStats() {
        return this.request('/admin/stats');
    }

    async getAdminReports(status = 'pending', page = 1) {
        return this.request(`/admin/reports?status=${status}&page=${page}`);
    }

    async getAdminUsers(page = 1, q = '') {
        return this.request(`/admin/users?page=${page}&q=${encodeURIComponent(q)}`);
    }

    async togglePostVisibility(id) {
        return this.request(`/admin/posts/${id}/toggle`, { method: 'POST' });
    }

    async banUser(id, reason) {
        return this.request(`/admin/users/${id}/ban`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        });
    }

    async unbanUser(id) {
        return this.request(`/admin/users/${id}/unban`, { method: 'POST' });
    }

    async reviewReport(id, action) {
        return this.request(`/admin/reports/${id}/review`, {
            method: 'POST',
            body: JSON.stringify({ action })
        });
    }
}

const api = new ApiService();
