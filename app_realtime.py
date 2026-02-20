"""
E-Commerce Returns Assistant - Production Real-Time Application
with Database Persistence, Real-Time Updates, and Analytics
"""

from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, timedelta
import json
import uuid
import os
from io import StringIO
import csv

from scaledown.returns import (
    PolicyCompressor,
    EligibilityEngine,
    ConversationHandler,
    Product,
    ReturnRequest,
    ConversationContext,
    ReturnReason,
    ReturnLabelGenerator,
    LabelConfig,
    MetricsTracker,
)

# Initialize Flask App
app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///returns_assistant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class Seller(db.Model):
    """Seller/Business Model"""
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100))
    policy_text = db.Column(db.Text)
    return_window_days = db.Column(db.Integer, default=30)
    refund_type = db.Column(db.String(50), default='full')
    refund_deduction_pct = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    returns = db.relationship('ReturnTicket', backref='seller', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'return_window_days': self.return_window_days,
            'refund_type': self.refund_type,
            'refund_deduction_pct': self.refund_deduction_pct,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class Customer(db.Model):
    """Customer Model"""
    id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    total_returns = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now)
    returns = db.relationship('ReturnTicket', backref='customer', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'total_returns': self.total_returns,
            'created_at': self.created_at.isoformat(),
        }


class ReturnTicket(db.Model):
    """Return Request Ticket Model - Core of the system"""
    id = db.Column(db.String(50), primary_key=True)
    seller_id = db.Column(db.String(50), db.ForeignKey('seller.id'), nullable=False)
    customer_id = db.Column(db.String(50), db.ForeignKey('customer.id'), nullable=False)
    
    # Product Info
    product_name = db.Column(db.String(200), nullable=False)
    product_sku = db.Column(db.String(100))
    category = db.Column(db.String(100))
    price = db.Column(db.Float)
    purchase_date = db.Column(db.DateTime)
    condition = db.Column(db.String(50))
    
    # Return Info
    reason = db.Column(db.String(50))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='initiated')
    eligibility_status = db.Column(db.String(50))
    
    # Exchange Option
    exchange_requested = db.Column(db.Boolean, default=False)
    exchange_product_id = db.Column(db.String(100))
    exchange_product_name = db.Column(db.String(200))
    
    # Refund Info
    refund_amount = db.Column(db.Float, default=0)
    deduction_reason = db.Column(db.Text)
    refund_status = db.Column(db.String(50), default='pending')
    
    # Tracking
    return_label_url = db.Column(db.String(500))
    return_tracking_number = db.Column(db.String(100))
    received_date = db.Column(db.DateTime)
    refunded_date = db.Column(db.DateTime)
    fraud_score = db.Column(db.Float, default=0)
    is_flagged = db.Column(db.Boolean, default=False)
    flag_reason = db.Column(db.Text)
    
    # Metadata
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'seller_id': self.seller_id,
            'customer_id': self.customer_id,
            'product_name': self.product_name,
            'product_sku': self.product_sku,
            'category': self.category,
            'price': self.price,
            'purchase_date': self.purchase_date.isoformat() if self.purchase_date else None,
            'condition': self.condition,
            'reason': self.reason,
            'description': self.description,
            'status': self.status,
            'eligibility_status': self.eligibility_status,
            'refund_amount': self.refund_amount,
            'refund_status': self.refund_status,
            'fraud_score': self.fraud_score,
            'is_flagged': self.is_flagged,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }


class Conversation(db.Model):
    """Chat Conversation History"""
    id = db.Column(db.String(50), primary_key=True)
    customer_id = db.Column(db.String(50), db.ForeignKey('customer.id'))
    return_ticket_id = db.Column(db.String(50), db.ForeignKey('return_ticket.id'))
    messages = db.Column(db.Text)  # JSON array
    sentiment = db.Column(db.String(50), default='neutral')
    frustration_level = db.Column(db.Float, default=0)
    escalated = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'return_ticket_id': self.return_ticket_id,
            'messages': json.loads(self.messages) if self.messages else [],
            'sentiment': self.sentiment,
            'frustration_level': self.frustration_level,
            'escalated': self.escalated,
            'created_at': self.created_at.isoformat(),
        }


# ============================================================================
# INITIALIZE RETURNS COMPONENTS
# ============================================================================

compressor = PolicyCompressor()
handlers_cache = {}
label_generator = ReturnLabelGenerator()
metrics_tracker = MetricsTracker()


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.route('/')
def index():
    """Home page"""
    return render_template('realtime.html')


# ========== SELLER ENDPOINTS ==========

@app.route('/api/sellers', methods=['GET'])
def get_sellers():
    """Get all sellers"""
    sellers = Seller.query.all()
    return jsonify([s.to_dict() for s in sellers])


@app.route('/api/sellers', methods=['POST'])
def create_seller():
    """Create a new seller"""
    try:
        data = request.json
        seller_id = f'seller_{uuid.uuid4().hex[:8]}'
        
        seller = Seller(
            id=seller_id,
            name=data.get('name'),
            email=data.get('email'),
            policy_text=data.get('policy_text', ''),
            return_window_days=data.get('return_window_days', 30),
            refund_type=data.get('refund_type', 'full'),
            refund_deduction_pct=data.get('refund_deduction_pct', 0)
        )
        
        db.session.add(seller)
        db.session.commit()
        
        return jsonify({'success': True, 'seller': seller.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/sellers/<seller_id>', methods=['GET'])
def get_seller(seller_id):
    """Get seller details"""
    seller = Seller.query.get(seller_id)
    if not seller:
        return jsonify({'success': False, 'error': 'Seller not found'}), 404
    return jsonify({'success': True, 'seller': seller.to_dict()})


@app.route('/api/sellers/<seller_id>/policy', methods=['POST'])
def update_policy(seller_id):
    """Update seller policy"""
    try:
        seller = Seller.query.get(seller_id)
        if not seller:
            return jsonify({'success': False, 'error': 'Seller not found'}), 404
        
        data = request.json
        policy_text = data.get('policy_text', '')
        
        # Parse policy
        policy = compressor.parse_policy(policy_text, seller_id, f"{seller.name} Policy")
        
        # Update seller
        seller.policy_text = policy_text
        seller.return_window_days = policy.return_window_days
        seller.refund_type = policy.refund_type
        seller.refund_deduction_pct = policy.refund_deduction_pct
        seller.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'seller': seller.to_dict(),
            'policy': {
                'return_window_days': policy.return_window_days,
                'refund_type': policy.refund_type,
                'refund_deduction_pct': policy.refund_deduction_pct,
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


# ========== CUSTOMER ENDPOINTS ==========

@app.route('/api/customers', methods=['GET'])
def get_customers():
    """Get all customers"""
    customers = Customer.query.all()
    return jsonify([c.to_dict() for c in customers])


@app.route('/api/customers', methods=['POST'])
def create_customer():
    """Create a new customer"""
    try:
        data = request.json
        customer_id = f'cust_{uuid.uuid4().hex[:8]}'
        
        customer = Customer(
            id=customer_id,
            name=data.get('name'),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address')
        )
        
        db.session.add(customer)
        db.session.commit()
        
        return jsonify({'success': True, 'customer': customer.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


# ========== RETURN ENDPOINTS ==========

@app.route('/api/returns', methods=['GET'])
def get_returns():
    """Get all returns with filters"""
    seller_id = request.args.get('seller_id')
    status = request.args.get('status')
    
    query = ReturnTicket.query
    
    if seller_id:
        query = query.filter_by(seller_id=seller_id)
    if status:
        query = query.filter_by(status=status)
    
    returns = query.order_by(ReturnTicket.created_at.desc()).all()
    return jsonify([r.to_dict() for r in returns])


@app.route('/api/returns', methods=['POST'])
def create_return():
    """Create a new return request"""
    try:
        data = request.json
        seller_id = data.get('seller_id')
        customer_id = data.get('customer_id')
        
        # Get seller
        seller = Seller.query.get(seller_id)
        if not seller:
            return jsonify({'success': False, 'error': 'Seller not found'}), 404
        
        # Get or create customer
        customer = Customer.query.get(customer_id)
        if not customer:
            customer = Customer(
                id=customer_id,
                name=data.get('customer_name', 'Customer'),
                email=data.get('customer_email')
            )
            db.session.add(customer)
        
        # Create return ticket
        return_id = f'ret_{uuid.uuid4().hex[:8]}'
        purchase_date = datetime.strptime(data.get('purchase_date'), '%Y-%m-%d')
        
        return_ticket = ReturnTicket(
            id=return_id,
            seller_id=seller_id,
            customer_id=customer_id,
            product_name=data.get('product_name'),
            product_sku=data.get('product_sku'),
            category=data.get('category'),
            price=float(data.get('price', 0)),
            purchase_date=purchase_date,
            condition=data.get('condition'),
            reason=data.get('reason'),
            description=data.get('description'),
        )
        
        # Check eligibility
        try:
            product = Product(
                product_id=return_id,
                name=return_ticket.product_name,
                category=return_ticket.category,
                price=return_ticket.price,
                purchase_date=purchase_date,
                condition=return_ticket.condition,
                seller_id=seller_id,
                seller_name=seller.name,
                sku=return_ticket.product_sku or 'SKU-001'
            )
            
            ret_req = ReturnRequest(
                return_id=return_id,
                customer_id=customer_id,
                product=product,
                reason=ReturnReason[data.get('reason', 'CHANGED_MIND').upper()],
                description=data.get('description', ''),
                reason_category=data.get('reason', 'other'),
            )
            
            # Use eligibility engine
            engine = EligibilityEngine(seller)  # Use seller as policy
            result = engine.check_eligibility(ret_req)
            
            return_ticket.eligibility_status = 'approved' if result.is_eligible else 'rejected'
            return_ticket.status = 'approved' if result.is_eligible else 'rejected'
            
            if result.is_eligible:
                refund_amount, deduction_reason = engine.calculate_refund_amount(ret_req)
                return_ticket.refund_amount = refund_amount
                return_ticket.deduction_reason = deduction_reason
                return_ticket.refund_status = 'approved'
            
            # Fraud detection
            fraud_score, _ = engine._check_fraud_patterns(ret_req)
            return_ticket.fraud_score = fraud_score
            return_ticket.is_flagged = fraud_score > 0.7
            
        except Exception as e:
            return_ticket.eligibility_status = 'pending'
            return_ticket.status = 'pending'
        
        db.session.add(return_ticket)
        if customer.total_returns is None:
            customer.total_returns = 1
        else:
            customer.total_returns += 1
        db.session.commit()
        
        return jsonify({'success': True, 'return': return_ticket.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/returns/<return_id>', methods=['GET'])
def get_return(return_id):
    """Get return details"""
    return_ticket = ReturnTicket.query.get(return_id)
    if not return_ticket:
        return jsonify({'success': False, 'error': 'Return not found'}), 404
    return jsonify({'success': True, 'return': return_ticket.to_dict()})


@app.route('/api/returns/<return_id>', methods=['PUT'])
def update_return(return_id):
    """Update return status"""
    try:
        return_ticket = ReturnTicket.query.get(return_id)
        if not return_ticket:
            return jsonify({'success': False, 'error': 'Return not found'}), 404
        
        data = request.json
        
        if 'status' in data:
            return_ticket.status = data['status']
        if 'refund_status' in data:
            return_ticket.refund_status = data['refund_status']
        if 'return_tracking_number' in data:
            return_ticket.return_tracking_number = data['return_tracking_number']
        if 'received_date' in data and data['received_date']:
            return_ticket.received_date = datetime.fromisoformat(data['received_date'])
        if 'refunded_date' in data and data['refunded_date']:
            return_ticket.refunded_date = datetime.fromisoformat(data['refunded_date'])
        if 'notes' in data:
            return_ticket.notes = data['notes']
        
        return_ticket.updated_at = datetime.now()
        db.session.commit()
        
        return jsonify({'success': True, 'return': return_ticket.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


# ========== LABEL GENERATION ENDPOINTS ==========

@app.route('/api/returns/<return_id>/generate-label', methods=['POST'])
def generate_return_label(return_id):
    """Generate return shipping label"""
    try:
        return_ticket = ReturnTicket.query.get(return_id)
        if not return_ticket:
            return jsonify({'success': False, 'error': 'Return not found'}), 404
        
        data = request.json or {}
        
        # Create label config
        config = LabelConfig(
            carrier=data.get('carrier', 'usps'),
            service_type=data.get('service_type', 'ground'),
            from_address={
                'name': 'Our Warehouse',
                'address': '123 Warehouse St',
                'city': 'Los Angeles',
                'state': 'CA',
                'zip': '90001',
                'country': 'US'
            },
            to_address={
                'name': return_ticket.customer.name,
                'address': 'Customer Address',
                'city': 'City',
                'state': 'State',
                'zip': '12345',
                'country': 'US'
            },
            weight_lbs=data.get('weight_lbs', 2.0),
            dimensions={
                'length': data.get('length', 12),
                'width': data.get('width', 8),
                'height': data.get('height', 6)
            }
        )
        
        # Generate label
        label = label_generator.generate_label(return_id, config)
        
        if label['success']:
            return_ticket.return_label_url = label.get('label_id')
            return_ticket.tracking_number = label.get('tracking_number')
            return_ticket.status = 'label_generated'
            return_ticket.updated_at = datetime.now()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'label': label,
                'return': return_ticket.to_dict()
            })
        else:
            return jsonify({'success': False, 'error': label.get('error')}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


# ========== CHAT ENDPOINTS ==========

@app.route('/api/chat', methods=['POST'])
def chat_message():
    """Handle chat messages"""
    try:
        data = request.json
        customer_id = data.get('customer_id')
        seller_id = data.get('seller_id')
        message = data.get('message')
        return_id = data.get('return_id')
        
        # Get or create conversation
        conv_id = data.get('conversation_id') or f'conv_{uuid.uuid4().hex[:8]}'
        conversation = Conversation.query.get(conv_id)
        
        if not conversation:
            conversation = Conversation(
                id=conv_id,
                customer_id=customer_id,
                return_ticket_id=return_id,
                messages=json.dumps([])
            )
            db.session.add(conversation)
        
        # Initialize handler if not cached
        seller = Seller.query.get(seller_id)
        if seller_id not in handlers_cache:
            handlers_cache[seller_id] = ConversationHandler({seller_id: seller})
        
        handler = handlers_cache[seller_id]
        
        # Create context
        context = ConversationContext(
            conversation_id=conv_id,
            customer_id=customer_id,
        )
        
        # Process message
        response, updated_context = handler.handle_message(context, message)
        
        # Save conversation
        messages = json.loads(conversation.messages or '[]')
        messages.append({'role': 'user', 'content': message})
        messages.append({'role': 'assistant', 'content': response})
        
        conversation.messages = json.dumps(messages)
        conversation.sentiment = updated_context.customer_sentiment
        conversation.frustration_level = updated_context.frustration_level
        conversation.escalated = updated_context.escalation_required
        conversation.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'response': response,
            'conversation_id': conv_id,
            'sentiment': updated_context.customer_sentiment,
            'frustration_level': updated_context.frustration_level,
            'escalated': updated_context.escalation_required,
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400


# ========== ANALYTICS ENDPOINTS ==========

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get system analytics"""
    try:
        seller_id = request.args.get('seller_id')
        
        query = ReturnTicket.query
        if seller_id:
            query = query.filter_by(seller_id=seller_id)
        
        all_returns = query.all()
        
        total_returns = len(all_returns)
        approved_returns = len([r for r in all_returns if r.status == 'approved'])
        rejected_returns = len([r for r in all_returns if r.status == 'rejected'])
        flagged_returns = len([r for r in all_returns if r.is_flagged])
        
        total_refunded = sum([r.refund_amount for r in all_returns if r.refund_status == 'completed'])
        
        return_reasons = {}
        for r in all_returns:
            reason = r.reason or 'unknown'
            return_reasons[reason] = return_reasons.get(reason, 0) + 1
        
        return jsonify({
            'success': True,
            'analytics': {
                'total_returns': total_returns,
                'approved_returns': approved_returns,
                'rejected_returns': rejected_returns,
                'flagged_returns': flagged_returns,
                'approval_rate': (approved_returns / total_returns * 100) if total_returns > 0 else 0,
                'total_refunded': total_refunded,
                'avg_refund': (total_refunded / approved_returns) if approved_returns > 0 else 0,
                'return_reasons': return_reasons,
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# ========== EXPORT ENDPOINTS ==========

@app.route('/api/export/returns', methods=['GET'])
def export_returns():
    """Export returns as CSV"""
    try:
        seller_id = request.args.get('seller_id')
        
        query = ReturnTicket.query
        if seller_id:
            query = query.filter_by(seller_id=seller_id)
        
        returns = query.all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Headers
        headers = [
            'Return ID', 'Customer ID', 'Product', 'Price', 'Reason', 
            'Status', 'Eligibility', 'Refund Amount', 'Fraud Score', 'Created Date'
        ]
        writer.writerow(headers)
        
        # Data rows
        for r in returns:
            writer.writerow([
                r.id,
                r.customer_id,
                r.product_name,
                r.price,
                r.reason,
                r.status,
                r.eligibility_status,
                r.refund_amount,
                r.fraud_score,
                r.created_at.isoformat()
            ])
        
        return jsonify({
            'success': True,
            'csv': output.getvalue()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# ========== METRICS ENDPOINTS ==========

@app.route('/api/metrics/benefits', methods=['GET'])
def get_benefits_report():
    """Get ScaleDown benefits report"""
    try:
        report = metrics_tracker.get_benefits_report()
        return jsonify({'success': True, 'report': report})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/metrics/reasons', methods=['GET'])
def get_reason_analysis():
    """Get analysis of return reasons"""
    try:
        all_returns = ReturnTicket.query.all()
        
        # Build reason summary
        reasons = {}
        for r in all_returns:
            reason = r.reason or 'unknown'
            reasons[reason] = reasons.get(reason, 0) + 1
        
        # Analyze
        return_data = [r.to_dict() for r in all_returns]
        analysis = metrics_tracker.analyze_return_reasons(reasons, return_data)
        
        return jsonify({
            'success': True,
            'analysis': [
                {
                    'reason': a.reason,
                    'count': a.count,
                    'percentage': round(a.percentage, 2),
                    'avg_refund': round(a.avg_refund_amount, 2),
                    'fraud_rate': round(a.fraud_rate, 2)
                }
                for a in analysis
            ]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║  E-Commerce Returns Assistant - REAL-TIME PRODUCTION APP       ║
    ╚════════════════════════════════════════════════════════════════╝
    
    🚀 Starting real-time server...
    
    Open your browser and go to: http://localhost:8000
    
    Features:
    ✅ Real-Time Data Persistence (SQLite)
    ✅ Return Ticket Management
    ✅ Customer Profiles
    ✅ Eligibility Checking
    ✅ Chat Support with History
    ✅ Real-Time Analytics
    ✅ Fraud Detection
    ✅ Data Export (CSV)
    ✅ Auto-Save on Every Action
    
    Database: returns_assistant.db (auto-created)
    
    Press Ctrl+C to stop the server
    """)
    
    app.run(debug=True, host='127.0.0.1', port=8000, use_reloader=False)
