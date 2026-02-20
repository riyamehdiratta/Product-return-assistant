// ====== Tab Navigation ======
function switchTab(tabName) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Remove active class from buttons
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    
    // Mark button as active
    event.target.classList.add('active');
}

// ====== Policy Compression ======
function loadSamplePolicy() {
    fetch('/api/sample-policy')
        .then(response => response.json())
        .then(data => {
            document.getElementById('policyText').value = data.policy_text;
        })
        .catch(error => alert('Error loading sample policy: ' + error));
}

function compressPolicy() {
    const sellerId = document.getElementById('sellerId').value || 'seller_' + Math.random().toString(36).substr(2, 9);
    const policyName = document.getElementById('policyName').value || 'Return Policy';
    const policyText = document.getElementById('policyText').value;
    
    if (!policyText.trim()) {
        alert('Please enter a policy text or load a sample');
        return;
    }
    
    fetch('/api/compress-policy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            seller_id: sellerId,
            policy_name: policyName,
            policy_text: policyText
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayPolicyResult(data.policy);
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => alert('Error: ' + error));
}

function displayPolicyResult(policy) {
    const output = document.getElementById('policyOutput');
    output.innerHTML = `
        <div class="result-item success">
            <strong>Seller ID:</strong> ${policy.seller_id}
        </div>
        <div class="result-item success">
            <strong>Return Window:</strong> ${policy.return_window_days} days
        </div>
        <div class="result-item success">
            <strong>Refund Type:</strong> ${policy.refund_type}
        </div>
        <div class="result-item success">
            <strong>Restocking Fee:</strong> ${policy.refund_deduction_pct}%
        </div>
        <div class="result-item success">
            <strong>Eligible Categories:</strong> ${policy.eligible_categories.join(', ')}
        </div>
        <div class="result-item success">
            <strong>Eligible Conditions:</strong> ${policy.eligible_conditions.join(', ')}
        </div>
        <div class="result-item success">
            <strong>Approval Time:</strong> ${policy.approval_time_hours} hours
        </div>
        <div class="result-item success">
            <strong>Refund Processing:</strong> ${policy.refund_time_days} business days
        </div>
        <div class="result-item success">
            <strong>Supports Replacement:</strong> ${policy.supports_replacement ? '✅ Yes' : '❌ No'}
        </div>
        <div class="result-item success">
            <strong>Supports Pickup:</strong> ${policy.supports_pickup ? '✅ Yes' : '❌ No'}
        </div>
    `;
    document.getElementById('policyResult').style.display = 'block';
}

// ====== Eligibility Checking ======
function checkEligibility() {
    const sellerId = document.getElementById('elgSellerId').value;
    const customerId = document.getElementById('customerId').value;
    const productName = document.getElementById('productName').value;
    const price = parseFloat(document.getElementById('productPrice').value);
    const category = document.getElementById('productCategory').value;
    const condition = document.getElementById('productCondition').value;
    const purchaseDate = document.getElementById('purchaseDate').value;
    const reason = document.getElementById('returnReason').value;
    
    if (!sellerId || !productName || !price || !purchaseDate) {
        alert('Please fill in all required fields');
        return;
    }
    
    fetch('/api/check-eligibility', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            seller_id: sellerId,
            customer_id: customerId,
            product_name: productName,
            price: price,
            category: category,
            condition: condition,
            purchase_date: purchaseDate,
            reason: reason
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayEligibilityResult(data);
        } else {
            alert('Error: ' + data.error);
        }
    })
    .catch(error => alert('Error: ' + error));
}

function displayEligibilityResult(data) {
    const output = document.getElementById('eligibilityOutput');
    const statusClass = data.eligible ? 'approved' : 'rejected';
    const statusText = data.eligible ? '✅ APPROVED' : '❌ REJECTED';
    
    let html = `<div class="status-badge ${statusClass}">${statusText}</div>`;
    
    if (data.checks_passed.length > 0) {
        html += '<h3>✓ Checks Passed:</h3>';
        data.checks_passed.forEach(check => {
            html += `<div class="result-item success">${check}</div>`;
        });
    }
    
    if (data.checks_failed.length > 0) {
        html += '<h3>✗ Checks Failed:</h3>';
        data.checks_failed.forEach(check => {
            html += `<div class="result-item error">${check}</div>`;
        });
    }
    
    if (data.reasons.length > 0) {
        html += '<h3>📝 Reasons:</h3>';
        data.reasons.forEach(reason => {
            html += `<div class="result-item">${reason}</div>`;
        });
    }
    
    if (data.suggestions.length > 0) {
        html += '<h3>💡 Suggestions:</h3>';
        data.suggestions.forEach(suggestion => {
            html += `<div class="result-item">${suggestion}</div>`;
        });
    }
    
    html += `<h3>💰 Refund Amount: $${data.refund_amount.toFixed(2)}</h3>`;
    html += `<div class="result-item">${data.deduction_reason}</div>`;
    
    output.innerHTML = html;
    document.getElementById('eligibilityResult').style.display = 'block';
}

// ====== Chat Support ======
let conversationId = null;

function sendMessage() {
    const sellerId = document.getElementById('chatSellerId').value;
    const customerName = document.getElementById('chatName').value;
    const messageInput = document.getElementById('chatInput');
    const message = messageInput.value.trim();
    
    if (!message) return;
    if (!sellerId) {
        alert('Please enter a seller ID');
        return;
    }
    
    // Display user message
    addChatMessage(message, 'user');
    messageInput.value = '';
    
    // Send to server
    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            seller_id: sellerId,
            customer_name: customerName,
            message: message,
            conversation_id: conversationId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            conversationId = data.conversation_id;
            addChatMessage(data.response, 'assistant');
            
            // Show sentiment
            document.getElementById('sentimentText').textContent = data.sentiment;
            document.getElementById('frustrationText').textContent = (data.frustration_level * 100).toFixed(0) + '%';
            document.getElementById('sentimentBox').style.display = 'block';
            
            if (data.escalation_required) {
                addChatMessage('⚠️ Your concern has been escalated to our support team.', 'assistant');
            }
        } else {
            addChatMessage('❌ Error: ' + data.error, 'assistant');
        }
    })
    .catch(error => addChatMessage('❌ Error: ' + error, 'assistant'));
}

function addChatMessage(message, role) {
    const messagesBox = document.getElementById('chatMessages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${role}`;
    messageDiv.textContent = message;
    messagesBox.appendChild(messageDiv);
    messagesBox.scrollTop = messagesBox.scrollHeight;
}

// ====== Analytics ======
function loadAnalytics() {
    fetch('/api/analytics')
        .then(response => response.json())
        .then(data => {
            displayAnalytics(data);
        })
        .catch(error => alert('Error: ' + error));
}

function displayAnalytics(data) {
    let html = `
        <div class="stats-grid">
            <div class="stat-card">
                <h4>Total Policies</h4>
                <div class="stat-value">${data.total_policies}</div>
            </div>
            <div class="stat-card">
                <h4>Active Conversations</h4>
                <div class="stat-value">${data.total_conversations}</div>
            </div>
        </div>
    `;
    
    if (data.policies.length > 0) {
        html += '<h3>Configured Policies:</h3>';
        data.policies.forEach(policy => {
            html += `
                <div class="result-item">
                    <strong>${policy.policy_name}</strong> (${policy.seller_id})<br>
                    Return Window: ${policy.return_window_days} days
                </div>
            `;
        });
    }
    
    document.getElementById('analyticsOutput').innerHTML = html;
    document.getElementById('analyticsResult').style.display = 'block';
}

// ====== Initialize ====== 
document.addEventListener('DOMContentLoaded', function() {
    // Load sample policy on page load
    loadSamplePolicy();
});
