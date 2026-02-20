// Real-Time Dashboard JavaScript

const API_BASE = '/api';

// State
let currentSeller = null;
let currentReturn = null;
let sellers = [];
let returns = [];

// Utility Functions
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            headers: { 'Content-Type': 'application/json' },
            ...options,
        });
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        showNotification('Error: ' + error.message, 'error');
        return null;
    }
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#10b981' : '#ef4444'};
        color: white;
        border-radius: 8px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

function updateClock() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleTimeString();
}

// Tab Navigation
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        document.getElementById(tab).classList.add('active');
        
        if (tab === 'sellers') loadSellers();
        if (tab === 'returns') loadReturns();
        if (tab === 'analytics') loadAnalytics();
    });
});

// ==================== DASHBOARD ====================

function updateDashboard() {
    fetch(`${API_BASE}/analytics`).then(r => r.json()).then(data => {
        if (data.success) {
            const stats = data.analytics;
            document.getElementById('metric-total').textContent = stats.total_returns;
            document.getElementById('metric-approved').textContent = stats.approved_returns;
            document.getElementById('metric-rejected').textContent = stats.rejected_returns;
            document.getElementById('metric-flagged').textContent = stats.flagged_returns;
        }
    });

    fetch(`${API_BASE}/returns?limit=10`).then(r => r.json()).then(rets => {
        if (Array.isArray(rets)) {
            const feed = document.getElementById('recent-returns-feed');
            if (rets.length === 0) {
                feed.innerHTML = '<div class="empty-state">No returns yet</div>';
            } else {
                feed.innerHTML = rets.map(r => `
                    <div class="feed-item">
                        <div class="feed-item-content">
                            <h4>${r.product_name}</h4>
                            <p>${r.reason} • $${r.price}</p>
                        </div>
                        <div class="feed-item-badge ${r.status}">${r.status}</div>
                    </div>
                `).join('');
            }
        }
    });
}

// ==================== SELLERS ====================

async function loadSellers() {
    const data = await apiCall('/sellers');
    if (!data || !Array.isArray(data)) return;
    
    sellers = data;
    const container = document.getElementById('sellers-container');
    
    if (sellers.length === 0) {
        container.innerHTML = '<div class="empty-state">No sellers yet. Create one to get started!</div>';
    } else {
        container.innerHTML = sellers.map(seller => `
            <div class="seller-card">
                <h3>${seller.name}</h3>
                <p>📧 ${seller.email || 'No email'}</p>
                <p>Return Window: <strong>${seller.return_window_days} days</strong></p>
                <p>Refund Type: <strong>${seller.refund_type}</strong></p>
                <p>Deduction: <strong>${seller.refund_deduction_pct}%</strong></p>
            </div>
        `).join('');
    }
    
    // Update seller filter in returns tab
    const filterSelect = document.getElementById('return-seller-filter');
    filterSelect.innerHTML = '<option value="">All Sellers</option>' + 
        sellers.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
    
    // Update seller select in return form
    const returnSelect = document.querySelector('#return-form select[name="seller_id"]');
    if (returnSelect) {
        returnSelect.innerHTML = '<option value="">Select Seller</option>' + 
            sellers.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
    }
}

document.getElementById('add-seller-btn')?.addEventListener('click', () => {
    document.getElementById('seller-modal').classList.add('active');
});

document.getElementById('seller-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    
    const response = await apiCall('/sellers', {
        method: 'POST',
        body: JSON.stringify(Object.fromEntries(formData))
    });
    
    if (response && response.success) {
        showNotification('✅ Seller created successfully!');
        document.getElementById('seller-modal').classList.remove('active');
        e.target.reset();
        loadSellers();
    }
});

// ==================== RETURNS ====================

async function loadReturns() {
    const data = await apiCall('/returns');
    if (!Array.isArray(data)) return;
    
    returns = data;
    renderReturnsTable();
}

function renderReturnsTable() {
    const tbody = document.getElementById('returns-tbody');
    
    if (returns.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="empty-state">No returns yet</td></tr>';
    } else {
        tbody.innerHTML = returns.map(r => `
            <tr>
                <td><strong>${r.id}</strong></td>
                <td>${r.product_name}</td>
                <td>${r.customer_id}</td>
                <td>${r.reason || 'N/A'}</td>
                <td><span style="padding:4px 8px; background:#e5e7eb; border-radius:4px; font-size:12px">${r.status}</span></td>
                <td>$${r.refund_amount.toFixed(2)}</td>
                <td>${r.fraud_score ? r.fraud_score.toFixed(2) : 'N/A'}</td>
                <td><button class="btn btn-small" onclick="viewReturn('${r.id}')">View</button></td>
            </tr>
        `).join('');
    }
}

document.getElementById('new-return-btn')?.addEventListener('click', () => {
    loadSellers();
    document.getElementById('return-modal').classList.add('active');
});

document.getElementById('return-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData);
    
    const response = await apiCall('/returns', {
        method: 'POST',
        body: JSON.stringify(data)
    });
    
    if (response && response.success) {
        showNotification('✅ Return created successfully!');
        document.getElementById('return-modal').classList.remove('active');
        e.target.reset();
        loadReturns();
        updateDashboard();
    }
});

function viewReturn(returnId) {
    const ret = returns.find(r => r.id === returnId);
    if (ret) {
        alert(`Return Details:\n\nID: ${ret.id}\nProduct: ${ret.product_name}\nStatus: ${ret.status}\nRefund: $${ret.refund_amount}`);
    }
}

// ==================== CHAT ====================

let conversations = [];

document.getElementById('chat-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const message = document.getElementById('chat-input').value.trim();
    if (!message) return;
    
    const conversationId = document.getElementById('current-conversation-id').value;
    if (!conversationId) {
        showNotification('Please select a conversation first', 'error');
        return;
    }
    
    const customerId = document.getElementById('current-customer-id').value;
    const sellerId = document.getElementById('current-seller-id').value;
    
    const response = await apiCall('/chat', {
        method: 'POST',
        body: JSON.stringify({
            conversation_id: conversationId,
            customer_id: customerId,
            seller_id: sellerId,
            message: message
        })
    });
    
    if (response && response.success) {
        document.getElementById('chat-input').value = '';
        displayChatMessage('user', message);
        displayChatMessage('assistant', response.response);
    }
});

function displayChatMessage(role, content) {
    const chatArea = document.getElementById('chat-area');
    if (chatArea.querySelector('.empty-state')) {
        chatArea.innerHTML = '';
    }
    
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-message ${role}`;
    msgDiv.textContent = content;
    chatArea.appendChild(msgDiv);
    chatArea.scrollTop = chatArea.scrollHeight;
}

// ==================== ANALYTICS ====================

async function loadAnalytics() {
    const data = await apiCall('/analytics');
    if (!data || !data.success) return;
    
    const stats = data.analytics;
    
    document.getElementById('approval-rate').textContent = stats.approval_rate.toFixed(1) + '%';
    document.getElementById('approval-progress').style.width = stats.approval_rate + '%';
    document.getElementById('total-refunded').textContent = '$' + stats.total_refunded.toFixed(2);
    document.getElementById('avg-refund').textContent = '$' + stats.avg_refund.toFixed(2);
    document.getElementById('flagged-count').textContent = stats.flagged_returns;
}

document.getElementById('export-csv-btn')?.addEventListener('click', async () => {
    const data = await apiCall('/export/returns');
    if (data && data.success) {
        const blob = new Blob([data.csv], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `returns_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        showNotification('✅ Data exported successfully!');
    }
});

// ==================== MODALS ====================

document.querySelectorAll('.close-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.target.closest('.modal').classList.remove('active');
    });
});

document.querySelectorAll('.close-modal').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.target.closest('.modal').classList.remove('active');
    });
});

document.querySelectorAll('.modal').forEach(modal => {
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('active');
    });
});

// ==================== INIT ====================

document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);
    
    updateDashboard();
    setInterval(updateDashboard, 5000); // Refresh every 5 seconds
    
    loadSellers();
});
