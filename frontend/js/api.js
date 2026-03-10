// =========================================================================
// ROCKYMIST FINMIS - API CLIENT v2
// =========================================================================

// FOR PRODUCTION: Replace with your actual Hugging Face Space URL
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://localhost:8000'
    : 'https://khanshahfahad-rockymist-mis.hf.space';

class ApiClient {
    static async login(username, password) {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        if (!res.ok) throw new Error('Invalid Credentials');
        return await res.json();
    }

    static async getCOA() {
        const res = await fetch(`${API_BASE}/data/coa`);
        return await res.json();
    }

    static async getCustomers(unit) {
        const res = await fetch(`${API_BASE}/data/customers/${unit}`);
        return await res.json();
    }

    static async analyzeAI(input, unit) {
        const res = await fetch(`${API_BASE}/transactions/ai/analyze`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_input: input, active_unit: unit })
        });
        if (!res.ok) throw new Error('AI Analysis Failed');
        return await res.json();
    }

    static async postAI(payload) {
        const res = await fetch(`${API_BASE}/transactions/ai/post`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Failed to post AI transaction');
        return await res.json();
    }

    static async postManual(payload) {
        const res = await fetch(`${API_BASE}/transactions/manual`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error('Failed to post manual transaction');
        return await res.json();
    }

    static async getJournal(start, end, unit) {
        const res = await fetch(`${API_BASE}/reports/journal?start=${start}&end=${end}&unit=${unit}`);
        return await res.json();
    }

    static async getMetrics(start, end) {
        const [cashRes, pnlRes] = await Promise.all([
            fetch(`${API_BASE}/reports/cash?end=${end}`),
            fetch(`${API_BASE}/reports/pnl?start=${start}&end=${end}`)
        ]);
        const cash = await cashRes.json();
        const pnl = await pnlRes.json();
        return { cash: cash.cash_balance, ...pnl };
    }

    static async getRecentTransactions() {
        const res = await fetch(`${API_BASE}/reports/recent`);
        return await res.json();
    }

    static async uploadPDF(file, unit) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('unit', unit);

        const res = await fetch(`${API_BASE}/transactions/pdf-sync`, {
            method: 'POST',
            body: formData
        });
        if (!res.ok) throw new Error('PDF Processing Failed');
        return await res.json();
    }
}
