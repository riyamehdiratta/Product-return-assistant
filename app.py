"""
E-Commerce Returns Assistant - Flask Web Application

Run this to start the web server on localhost:5000
"""

from flask import Flask, render_template, request, jsonify, session
from datetime import datetime, timedelta
import json
import uuid

from scaledown.returns import (
    PolicyCompressor,
    EligibilityEngine,
    ConversationHandler,
    Product,
    ReturnRequest,
    ConversationContext,
    ReturnReason,
)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = 'returns-assistant-secret-key-2026'

# Initialize components
compressor = PolicyCompressor()
conversation_handlers = {}
policies = {}
conversations = {}

# Sample policy for demo
SAMPLE_POLICY_TEXT = """
ELECTRONICS RETURN POLICY - Version 2.0

Thank you for your purchase! We want you to be completely satisfied with your 
purchase. If you're not happy, we offer returns within specific timeframes.

RETURN WINDOW
You have thirty (30) days from the date of purchase to return your item.

ELIGIBLE ITEMS
Electronics in original packaging, unopened, or in like-new condition.
Includes: computers, phones, cameras, headphones, and accessories.

RESTOCKING FEE
A 15% restocking fee applies to all electronics returns to cover our handling
and processing costs.

NON-RETURNABLE ITEMS
- Items used extensively
- Opened software or digital products
- Custom-configured computers
- Clearance/final sale items marked as such

REFUND PROCESSING
- Approval: Within 24 hours of receiving your return
- Processing: 5-7 business days for refund to appear in your account

RETURN OPTIONS
- Standard mail: We'll email you a prepaid return label
- Replacement: Same item or similar product available

ORIGINAL PACKAGING
Items should be returned in original packaging when possible.
"""


@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')


@app.route('/api/compress-policy', methods=['POST'])
def compress_policy():
    """Compress a return policy"""
    try:
        data = request.json
        policy_text = data.get('policy_text', SAMPLE_POLICY_TEXT)
        seller_id = data.get('seller_id', f'seller_{uuid.uuid4().hex[:8]}')
        policy_name = data.get('policy_name', 'Return Policy')
        
        # Compress policy
        policy = compressor.parse_policy(policy_text, seller_id, policy_name)
        
        # Store policy
        policies[seller_id] = policy
        
        # Initialize conversation handler for this seller
        conversation_handlers[seller_id] = ConversationHandler({seller_id: policy})
        
        return jsonify({
            'success': True,
            'policy': {
                'seller_id': policy.seller_id,
                'policy_name': policy.policy_name,
                'return_window_days': policy.return_window_days,
                'refund_type': policy.refund_type,
                'refund_deduction_pct': policy.refund_deduction_pct,
                'eligible_categories': policy.eligible_categories,
                'eligible_conditions': policy.eligible_conditions,
                'exclusions': policy.exclusions,
                'final_sale_items': policy.final_sale_items,
                'approval_time_hours': policy.approval_time_hours,
                'refund_time_days': policy.refund_time_days,
                'supports_replacement': policy.supports_replacement,
                'supports_pickup': policy.supports_pickup,
                'requires_original_packaging': policy.requires_original_packaging,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/check-eligibility', methods=['POST'])
def check_eligibility():
    """Check return eligibility"""
    try:
        data = request.json
        seller_id = data.get('seller_id')
        
        if seller_id not in policies:
            return jsonify({'success': False, 'error': 'Seller policy not found'}), 404
        
        policy = policies[seller_id]
        
        # Create product
        purchase_date = datetime.strptime(data.get('purchase_date'), '%Y-%m-%d')
        product = Product(
            product_id=f'prod_{uuid.uuid4().hex[:8]}',
            name=data.get('product_name', 'Product'),
            category=data.get('category', 'electronics'),
            price=float(data.get('price', 0)),
            purchase_date=purchase_date,
            condition=data.get('condition', 'new'),
            seller_id=seller_id,
            seller_name=data.get('seller_name', 'Seller'),
            sku=data.get('sku', 'SKU-001'),
        )
        
        # Create return request
        return_request = ReturnRequest(
            return_id=f'ret_{uuid.uuid4().hex[:8]}',
            customer_id=data.get('customer_id', f'cust_{uuid.uuid4().hex[:8]}'),
            product=product,
            reason=ReturnReason[data.get('reason', 'CHANGED_MIND').upper()],
            description=data.get('description', ''),
            reason_category=data.get('reason', 'other'),
        )
        
        # Check eligibility
        engine = EligibilityEngine(policy)
        result = engine.check_eligibility(return_request)
        
        # Calculate refund
        refund_amount, deduction_reason = engine.calculate_refund_amount(return_request)
        
        return jsonify({
            'success': True,
            'eligible': result.is_eligible,
            'checks_passed': result.checks_passed,
            'checks_failed': result.checks_failed,
            'reasons': result.reasons,
            'warnings': result.warnings,
            'suggestions': result.suggestions,
            'refund_amount': refund_amount,
            'deduction_reason': deduction_reason,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.json
        seller_id = data.get('seller_id')
        message = data.get('message')
        
        if seller_id not in conversation_handlers:
            return jsonify({'success': False, 'error': 'Seller not configured'}), 404
        
        # Get or create conversation
        conv_id = data.get('conversation_id') or f'conv_{uuid.uuid4().hex[:8]}'
        
        if conv_id not in conversations:
            conversations[conv_id] = ConversationContext(
                conversation_id=conv_id,
                customer_id=data.get('customer_id', f'cust_{uuid.uuid4().hex[:8]}'),
                customer_name=data.get('customer_name', 'Customer'),
                policy_context=policies.get(seller_id),
            )
        
        context = conversations[conv_id]
        handler = conversation_handlers[seller_id]
        
        # Process message
        response, updated_context = handler.handle_message(context, message)
        conversations[conv_id] = updated_context
        
        return jsonify({
            'success': True,
            'response': response,
            'conversation_id': conv_id,
            'sentiment': updated_context.customer_sentiment,
            'frustration_level': updated_context.frustration_level,
            'escalation_required': updated_context.escalation_required,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/sample-policy', methods=['GET'])
def get_sample_policy():
    """Get sample policy text"""
    return jsonify({'policy_text': SAMPLE_POLICY_TEXT})


@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get system analytics"""
    return jsonify({
        'total_policies': len(policies),
        'total_conversations': len(conversations),
        'policies': [
            {
                'seller_id': p.seller_id,
                'policy_name': p.policy_name,
                'return_window_days': p.return_window_days,
            }
            for p in policies.values()
        ]
    })


if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║  E-Commerce Returns Assistant - Web Application                ║
    ╚════════════════════════════════════════════════════════════════╝
    
    🚀 Starting web server...
    
    Open your browser and go to: http://localhost:8000
    
    Features:
    ✅ Policy Compression
    ✅ Eligibility Checking
    ✅ Conversational Chat
    ✅ Real-time Analytics
    ✅ Fraud Detection
    
    Press Ctrl+C to stop the server
    """)
    
    app.run(debug=True, host='127.0.0.1', port=8000)
