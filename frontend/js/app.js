// =========================================================================
// ROCKYMIST FINMIS v2 — APP LOGIC
// =========================================================================

// --- STATE ---
const state = {
    user: null,
    role: null,
    activeUnit: 'RockyMist_I',
    coa: [],
    customers: [],
    aiBuffer: null
};

// --- HELPERS ---
const $ = id => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);
const todayStr = new Date().toISOString().split('T')[0];
const yearStart = new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0];

const formatPKR = (n) => {
    const num = parseFloat(n) || 0;
    return 'PKR ' + num.toLocaleString('en-PK', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
};

function showToast(msg) {
    const toast = $('toast');
    $('toast-msg').textContent = msg;
    toast.classList.remove('hidden');
    clearTimeout(toast._timer);
    toast._timer = setTimeout(() => toast.classList.add('hidden'), 3500);
}

// --- INIT ---
document.addEventListener('DOMContentLoaded', () => {
    $('man-date').value = todayStr;
    $('rep-start').value = yearStart;
    $('rep-end').value = todayStr;

    // Display today's date in header
    const hd = $('header-date');
    if (hd) {
        hd.textContent = new Date().toLocaleDateString('en-US', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });
    }
});

// ============ AUTHENTICATION ============
$('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const loginBtn = $('login-btn');
    loginBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Authenticating...</span>';

    try {
        const res = await ApiClient.login($('username').value, $('password').value);
        state.user = res.username;
        state.role = res.role;
        $('display-user').textContent = res.username;
        $('display-role').textContent = res.role;

        $('login-container').classList.add('hidden');
        $('dashboard-container').classList.remove('hidden');

        await loadDropdowns();
        await loadDashboard();
        showToast('Welcome back, ' + res.username + '!');
    } catch (err) {
        $('login-error').classList.remove('hidden');
    } finally {
        loginBtn.innerHTML = '<span>Authenticate</span> <i class="fa-solid fa-arrow-right"></i>';
    }
});

$('logout-btn').addEventListener('click', () => {
    state.user = null;
    $('dashboard-container').classList.add('hidden');
    $('login-container').classList.remove('hidden');
    $('login-form').reset();
    $('login-error').classList.add('hidden');
});

// ============ NAVIGATION ============
$$('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
        $$('.nav-item').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const target = btn.dataset.target;
        $$('.view-section').forEach(sec => {
            sec.classList.toggle('active', sec.id === target);
            sec.classList.toggle('hidden', sec.id !== target);
        });

        if (target === 'view-dashboard') loadDashboard();
        if (target === 'view-reports') loadReports();
    });
});

// Entry tabs
$$('.entry-tab').forEach(btn => {
    btn.addEventListener('click', () => {
        $$('.entry-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const target = btn.dataset.tab;
        $$('.tab-panel').forEach(tp => {
            tp.classList.toggle('active', tp.id === target);
            tp.classList.toggle('hidden', tp.id !== target);
        });
    });
});

// Unit selector
$('active-unit').addEventListener('change', async (e) => {
    state.activeUnit = e.target.value;
    await loadDropdowns();
    showToast('Switched to ' + state.activeUnit);
});

// ============ DATA BINDING ============
async function loadDropdowns() {
    try {
        const [coaRes, custRes] = await Promise.all([
            ApiClient.getCOA(),
            ApiClient.getCustomers(state.activeUnit)
        ]);

        state.coa = coaRes.coa;
        state.customers = custRes.customers;

        const coaHtml = state.coa.map(c => `<option value="${c}">${c}</option>`).join('');
        const custHtml = state.customers.map(c => `<option value="${c}">${c}</option>`).join('');

        $('man-dr').innerHTML = coaHtml;
        $('man-cr').innerHTML = coaHtml;
        $('man-party').innerHTML = custHtml;
    } catch (e) {
        console.error('Failed loading dropdowns:', e);
    }
}

// ============ DASHBOARD VIEW ============
async function loadDashboard() {
    try {
        // Load KPIs
        const metrics = await ApiClient.getMetrics(yearStart, todayStr);
        $('dash-cash').textContent = formatPKR(metrics.cash);
        $('dash-revenue').textContent = formatPKR(metrics.revenue);
        $('dash-expense').textContent = formatPKR(metrics.expenses);
        $('dash-net').textContent = formatPKR(metrics.net);

        // Style net P&L color
        const netEl = $('dash-net');
        netEl.style.color = metrics.net >= 0 ? 'var(--success)' : 'var(--danger)';

        // Load recent transactions
        const { transactions } = await ApiClient.getRecentTransactions();
        const tbody = $('recent-txn-body');

        if (transactions && transactions.length > 0) {
            tbody.innerHTML = transactions.map(t => {
                const dr = parseFloat(t.Debit || 0);
                const cr = parseFloat(t.Credit || 0);
                return `<tr>
                    <td>${t.Date || '-'}</td>
                    <td>${t.Description || '-'}</td>
                    <td>${t.Account || '-'}</td>
                    <td>${t.Party || '-'}</td>
                    <td class="cell-debit">${dr > 0 ? dr.toLocaleString() : ''}</td>
                    <td class="cell-credit">${cr > 0 ? cr.toLocaleString() : ''}</td>
                    <td><span style="font-size:0.75rem;opacity:0.6">${t.Source || '-'}</span></td>
                </tr>`;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="7" class="empty-state"><i class="fa-solid fa-inbox"></i> No transactions yet</td></tr>';
        }
    } catch (e) {
        console.error('Dashboard load error:', e);
    }
}

// ============ AI SMART ENTRY ============
$('btn-analyze-ai').addEventListener('click', async () => {
    const input = $('ai-input').value.trim();
    if (!input) return;

    const btn = $('btn-analyze-ai');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Cerebras is thinking...</span>';
    btn.disabled = true;

    try {
        const analysis = await ApiClient.analyzeAI(input, state.activeUnit);
        state.aiBuffer = analysis;

        $('ai-outcome-text').textContent = analysis.outcome || 'Transaction parsed successfully';
        $('ai-dr').textContent = analysis.dr;
        $('ai-cr').textContent = analysis.cr;
        $('ai-amt').textContent = parseFloat(analysis.amt).toLocaleString();
        $('ai-party').textContent = analysis.party;

        $('ai-result-box').classList.remove('hidden');
    } catch (e) {
        showToast('AI Analysis Failed — Check Cerebras Token');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> <span>Analyze with Cerebras AI</span>';
        btn.disabled = false;
    }
});

$('btn-post-ai').addEventListener('click', async () => {
    if (!state.aiBuffer) return;

    const btn = $('btn-post-ai');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Posting...';
    btn.disabled = true;

    try {
        await ApiClient.postAI({
            entry_date: todayStr,
            active_unit: state.activeUnit,
            party: state.aiBuffer.party,
            dr_acc: state.aiBuffer.dr,
            cr_acc: state.aiBuffer.cr,
            amt: parseFloat(state.aiBuffer.amt),
            desc: state.aiBuffer.description || state.aiBuffer.outcome || '',
            user_id: state.user
        });
        showToast('AI Entry posted to Google Sheets!');
        $('ai-result-box').classList.add('hidden');
        $('ai-input').value = '';
        state.aiBuffer = null;
    } catch (err) {
        showToast('Post Failed');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Approve & Post to Google Sheets';
        btn.disabled = false;
    }
});

// ============ MANUAL ENTRY ============
$('manual-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        await ApiClient.postManual({
            entry_date: $('man-date').value,
            active_unit: state.activeUnit,
            party: $('man-party').value,
            dr_acc: $('man-dr').value,
            cr_acc: $('man-cr').value,
            amt: parseFloat($('man-amt').value),
            desc: $('man-desc').value,
            user_id: state.user
        });
        showToast('Manual Entry posted to Google Sheets!');
        $('manual-form').reset();
        $('man-date').value = todayStr;
    } catch (err) {
        showToast('Manual Post Failed');
    }
});

// ============ REPORTS ============
async function loadReports() {
    const s = $('rep-start').value;
    const e = $('rep-end').value;
    try {
        const metrics = await ApiClient.getMetrics(s, e);
        $('metric-cash').textContent = formatPKR(metrics.cash);
        $('metric-pnl').textContent = formatPKR(metrics.net);
        $('metric-pnl').style.color = metrics.net >= 0 ? 'var(--success)' : 'var(--danger)';
        $('metric-pnl-sub').textContent = `Rev: ${formatPKR(metrics.revenue)} | Exp: ${formatPKR(metrics.expenses)}`;

        const { journal } = await ApiClient.getJournal(s, e, state.activeUnit);

        if (journal.length > 0) {
            $('journal-body').innerHTML = journal.map(r => `
                <tr>
                    <td>${r.date}</td>
                    <td>${r.description}</td>
                    <td>${r.account}</td>
                    <td>${r.party}</td>
                    <td class="cell-debit">${r.debit > 0 ? r.debit.toLocaleString() : ''}</td>
                    <td class="cell-credit">${r.credit > 0 ? r.credit.toLocaleString() : ''}</td>
                </tr>
            `).join('');
            $('journal-container').classList.remove('hidden');
        } else {
            $('journal-body').innerHTML = '<tr><td colspan="6" class="empty-state"><i class="fa-solid fa-inbox"></i> No records found for this period</td></tr>';
            $('journal-container').classList.remove('hidden');
        }
    } catch (err) {
        showToast('Failed to load reports');
    }
}

$('btn-fetch-reports').addEventListener('click', loadReports);

// ============ PDF SYNC ============
const dropzone = $('dropzone');
const pdfInput = $('pdf-upload');
let pendingFile = null;

// Click to browse
dropzone.addEventListener('click', () => pdfInput.click());

// Drag & Drop
dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('drag-active');
});
dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('drag-active');
});
dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('drag-active');
    const file = e.dataTransfer.files[0];
    if (file && file.type === 'application/pdf') {
        handlePDFSelect(file);
    }
});

pdfInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file && file.type === 'application/pdf') {
        handlePDFSelect(file);
    }
});

function handlePDFSelect(file) {
    pendingFile = file;
    const nameEl = $('dropzone-filename');
    nameEl.querySelector('span').textContent = file.name;
    nameEl.classList.remove('hidden');
    dropzone.querySelector('h3').textContent = 'File Selected!';
    dropzone.style.borderColor = 'var(--success)';
    $('btn-process-pdf').disabled = false;
}

$('btn-process-pdf').addEventListener('click', async () => {
    if (!pendingFile) return;
    const btn = $('btn-process-pdf');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Cerebras is analyzing...';
    btn.disabled = true;

    try {
        const res = await ApiClient.uploadPDF(pendingFile, state.activeUnit);
        const outcome = typeof res.ai_analysis === 'object'
            ? JSON.stringify(res.ai_analysis, null, 2)
            : (res.ai_analysis || 'Analysis complete');

        $('pdf-ai-outcome').textContent = outcome;
        $('pdf-raw-text').textContent = res.text_preview || 'No text extracted';
        $('pdf-result').classList.remove('hidden');
        showToast('Bank Statement Analyzed Successfully!');
    } catch (e) {
        showToast('PDF Analysis Failed');
    } finally {
        btn.innerHTML = '<i class="fa-solid fa-microchip"></i> Analyze with Cerebras AI';
        btn.disabled = false;
    }
});
