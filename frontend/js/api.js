/**
 * ResumeAI Centralized API Client
 * Decoupled client communicating with Flask REST API.
 */

const API = (() => {
  const STORAGE_TOKEN_KEY = 'resume_token';
  const STORAGE_USER_KEY = 'resume_user';

  const getBaseUrl = () => {
    if (window.API_BASE_URL) return window.API_BASE_URL.replace(/\/+$/, '');
    const custom = localStorage.getItem('API_BASE_URL');
    if (custom) return custom.replace(/\/+$/, '');
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1' || window.location.protocol === 'file:') {
      return 'http://127.0.0.1:5000';
    }
    return ''; // Relative path in production if deployed behind reverse proxy
  };

  const getToken = () => localStorage.getItem(STORAGE_TOKEN_KEY);
  const setToken = (tok) => {
    if (tok) localStorage.setItem(STORAGE_TOKEN_KEY, tok);
    else localStorage.removeItem(STORAGE_TOKEN_KEY);
  };

  const getUser = () => {
    try {
      const raw = localStorage.getItem(STORAGE_USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  };
  const setUser = (usr) => {
    if (usr) localStorage.setItem(STORAGE_USER_KEY, JSON.stringify(usr));
    else localStorage.removeItem(STORAGE_USER_KEY);
  };

  const clearAuth = () => {
    localStorage.removeItem(STORAGE_TOKEN_KEY);
    localStorage.removeItem(STORAGE_USER_KEY);
  };

  const isAuthenticated = () => Boolean(getToken());

  async function request(endpoint, options = {}) {
    const base = getBaseUrl();
    const url = endpoint.startsWith('http') ? endpoint : `${base}${endpoint}`;
    const headers = options.headers ? { ...options.headers } : {};

    const token = getToken();
    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const fetchOpts = {
      ...options,
      headers,
      credentials: 'include'
    };

    let response;
    try {
      response = await fetch(url, fetchOpts);
    } catch (netErr) {
      throw new Error(`Unable to reach backend server at ${base || window.location.origin}. Please ensure the Flask backend is running on port 5000.`);
    }

    if (response.status === 401) {
      clearAuth();
      const path = window.location.pathname.toLowerCase();
      const isPublic = path.endsWith('index.html') ||
                       path.endsWith('login.html') ||
                       path.endsWith('register.html') ||
                       path === '/' ||
                       path.endsWith('/');
      if (!isPublic) {
        window.location.href = 'login.html';
      }
    }

    let payload;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
    } else {
      payload = await response.text();
    }

    if (!response.ok) {
      const msg = (payload && payload.error) || (typeof payload === 'string' && payload) || `Request failed (${response.status})`;
      const err = new Error(msg);
      err.status = response.status;
      err.data = payload;
      throw err;
    }

    return payload;
  }

  return {
    getBaseUrl,
    getToken,
    setToken,
    getUser,
    setUser,
    clearAuth,
    isAuthenticated,

    // Auth
    auth: {
      async register(userData) {
        const res = await request('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify(userData)
        });
        if (res.token) setToken(res.token);
        if (res.user) setUser(res.user);
        return res;
      },
      async login(credentials) {
        const res = await request('/api/auth/login', {
          method: 'POST',
          body: JSON.stringify(credentials)
        });
        if (res.token) setToken(res.token);
        if (res.user) setUser(res.user);
        return res;
      },
      async logout() {
        try {
          await request('/api/auth/logout', { method: 'POST' });
        } catch {
          // Ignore network errors on logout
        } finally {
          clearAuth();
        }
      },
      async me() {
        const res = await request('/api/auth/me', { method: 'GET' });
        if (res.user) setUser(res.user);
        return res;
      },
      async updateProfile(profileData) {
        const res = await request('/api/auth/profile', {
          method: 'PUT',
          body: JSON.stringify(profileData)
        });
        if (res.user) setUser(res.user);
        return res;
      }
    },

    // Resumes
    resumes: {
      async list() {
        return request('/api/resumes', { method: 'GET' });
      },
      async upload(formData) {
        return request('/api/resumes/upload', {
          method: 'POST',
          body: formData
        });
      },
      async getText(id) {
        return request(`/api/resumes/${id}/text`, { method: 'GET' });
      },
      getFileUrl(id) {
        const base = getBaseUrl();
        return `${base}/api/resumes/${id}/file`;
      },
      async delete(id) {
        return request(`/api/resumes/${id}`, { method: 'DELETE' });
      }
    },

    // Analysis
    analysis: {
      async run(kind, data) {
        return request(`/api/analysis/run/${kind}`, {
          method: 'POST',
          body: JSON.stringify(data)
        });
      },
      async history() {
        return request('/api/analysis/history', { method: 'GET' });
      },
      async get(kind, id) {
        return request(`/api/analysis/${kind}/${id}`, { method: 'GET' });
      }
    },

    // Dashboard
    dashboard: {
      async getData() {
        return request('/api/dashboard', { method: 'GET' });
      }
    }
  };
})();

window.API = API;
