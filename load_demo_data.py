#!/usr/bin/env python
"""
Demo Data Generator - Populate the database with sample data
for testing the real-time application
"""

import requests
import json
from datetime import datetime, timedelta

API_BASE = 'http://localhost:8000/api'

def create_seller():
    """Create sample sellers"""
    sellers_data = [
        {
            'name': 'TechGear Electronics',
            'email': 'support@techgear.com',
            'policy_text': 'We accept returns within 30 days of purchase. Full refund for defective items.',
            'return_window_days': 30,
            'refund_type': 'full',
            'refund_deduction_pct': 0
        },
        {
            'name': 'Fashion Forward',
            'email': 'help@fashionforward.com',
            'policy_text': 'Returns accepted within 60 days. 15% restocking fee applies.',
            'return_window_days': 60,
            'refund_type': 'partial',
            'refund_deduction_pct': 15
        }
    ]
    
    created = []
    for seller_data in sellers_data:
        response = requests.post(f'{API_BASE}/sellers', json=seller_data)
        if response.status_code == 201:
            seller = response.json()['seller']
            created.append(seller)
            print(f"✅ Created seller: {seller['name']} (ID: {seller['id']})")
        else:
            print(f"❌ Failed to create seller: {seller_data['name']}")
    
    return created

def create_returns(sellers):
    """Create sample return requests"""
    if not sellers:
        print("⚠️  No sellers found. Create sellers first.")
        return
    
    returns_data = [
        {
            'seller_id': sellers[0]['id'],
            'customer_id': 'cust_001',
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'product_name': 'Wireless Headphones',
            'product_sku': 'WH-001',
            'category': 'Electronics',
            'price': 149.99,
            'purchase_date': (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
            'condition': 'like_new',
            'reason': 'DEFECTIVE',
            'description': 'Left speaker not working properly'
        },
        {
            'seller_id': sellers[0]['id'],
            'customer_id': 'cust_002',
            'customer_name': 'Jane Smith',
            'customer_email': 'jane@example.com',
            'product_name': 'USB-C Cable',
            'product_sku': 'USB-002',
            'category': 'Accessories',
            'price': 29.99,
            'purchase_date': (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'),
            'condition': 'good',
            'reason': 'CHANGED_MIND',
            'description': 'Changed my mind, no longer needed'
        },
        {
            'seller_id': sellers[1]['id'],
            'customer_id': 'cust_003',
            'customer_name': 'Robert Johnson',
            'customer_email': 'robert@example.com',
            'product_name': 'Cotton T-Shirt',
            'product_sku': 'SHIRT-101',
            'category': 'Clothing',
            'price': 39.99,
            'purchase_date': (datetime.now() - timedelta(days=15)).strftime('%Y-%m-%d'),
            'condition': 'like_new',
            'reason': 'NOT_AS_DESCRIBED',
            'description': 'Color is different than shown in pictures'
        },
        {
            'seller_id': sellers[1]['id'],
            'customer_id': 'cust_004',
            'customer_name': 'Emma Davis',
            'customer_email': 'emma@example.com',
            'product_name': 'Jeans',
            'product_sku': 'JEANS-205',
            'category': 'Clothing',
            'price': 79.99,
            'purchase_date': (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
            'condition': 'new',
            'reason': 'DAMAGED',
            'description': 'Arrived with tear in the seam'
        }
    ]
    
    for return_data in returns_data:
        response = requests.post(f'{API_BASE}/returns', json=return_data)
        if response.status_code == 201:
            return_obj = response.json()['return']
            print(f"✅ Created return: {return_obj['product_name']} (ID: {return_obj['id']}, Status: {return_obj['status']})")
        else:
            print(f"❌ Failed to create return: {return_data['product_name']}")
            print(f"   Response: {response.text}")

def main():
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║  Real-Time App - Demo Data Generator                          ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        print("\n📝 Creating sample sellers...")
        sellers = create_seller()
        
        print("\n📦 Creating sample returns...")
        create_returns(sellers)
        
        print("""
    ✅ Demo data created successfully!
    
    Next steps:
    1. Go to http://localhost:8000
    2. Check Dashboard for live metrics
    3. View Returns tab to see created returns
    4. Check Analytics for statistics
    5. Try Chat support
    
    🗄️  All data is persisted in returns_assistant.db
        """)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("   Make sure the real-time app is running on http://localhost:8000")

if __name__ == '__main__':
    main()
