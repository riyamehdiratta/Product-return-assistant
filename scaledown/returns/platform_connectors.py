"""
E-Commerce Platform Connectors
Integrates with Shopify, WooCommerce, and other platforms
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
import hashlib
import hmac
import json


@dataclass
class Order:
    """Universal order model"""
    order_id: str
    platform: str
    customer_id: str
    customer_email: str
    customer_name: str
    order_date: datetime
    items: List[Dict[str, Any]]
    total_amount: float
    currency: str = "USD"
    shipping_address: Optional[Dict] = None


@dataclass
class ReturnLabel:
    """Return shipping label"""
    label_id: str
    carrier: str
    tracking_number: str
    shipping_label_url: str
    qr_code: str
    barcode: str
    estimated_delivery: datetime
    cost: float = 0.0


class PlatformConnector(ABC):
    """Base class for e-commerce platform connectors"""
    
    def __init__(self, api_key: str, store_url: str):
        self.api_key = api_key
        self.store_url = store_url
    
    @abstractmethod
    def authenticate(self) -> bool:
        """Verify API credentials"""
        pass
    
    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """Retrieve order from platform"""
        pass
    
    @abstractmethod
    def get_orders(self, customer_id: str) -> List[Order]:
        """Get all orders for a customer"""
        pass
    
    @abstractmethod
    def create_refund(self, order_id: str, amount: float, reason: str) -> Dict:
        """Process refund on platform"""
        pass
    
    @abstractmethod
    def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order/return status on platform"""
        pass


class ShopifyConnector(PlatformConnector):
    """Shopify API connector"""
    
    def __init__(self, api_key: str, store_url: str, access_token: str):
        super().__init__(api_key, store_url)
        self.access_token = access_token
        self.api_version = "2024-01"
        self.base_url = f"https://{store_url}/admin/api/{self.api_version}"
    
    def authenticate(self) -> bool:
        """Verify Shopify API credentials"""
        try:
            headers = {
                'X-Shopify-Access-Token': self.access_token,
                'Content-Type': 'application/json'
            }
            # Test API call
            response = self._make_request('GET', '/shop.json', headers)
            return response is not None
        except Exception as e:
            print(f"Shopify authentication failed: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get Shopify order by ID"""
        try:
            headers = {'X-Shopify-Access-Token': self.access_token}
            response = self._make_request('GET', f'/orders/{order_id}.json', headers)
            
            if response and 'order' in response:
                order_data = response['order']
                return self._convert_shopify_order(order_data)
            return None
        except Exception as e:
            print(f"Error fetching Shopify order: {e}")
            return None
    
    def get_orders(self, customer_id: str) -> List[Order]:
        """Get all Shopify orders for customer"""
        try:
            headers = {'X-Shopify-Access-Token': self.access_token}
            response = self._make_request(
                'GET', 
                f'/customers/{customer_id}/orders.json',
                headers
            )
            
            if response and 'orders' in response:
                return [self._convert_shopify_order(o) for o in response['orders']]
            return []
        except Exception as e:
            print(f"Error fetching Shopify orders: {e}")
            return []
    
    def create_refund(self, order_id: str, amount: float, reason: str) -> Dict:
        """Create refund in Shopify"""
        try:
            headers = {'X-Shopify-Access-Token': self.access_token}
            refund_data = {
                'refund': {
                    'note': f'Return: {reason}',
                    'transactions': [
                        {'parent_id': order_id, 'amount': str(amount)}
                    ]
                }
            }
            
            response = self._make_request(
                'POST',
                f'/orders/{order_id}/refunds.json',
                headers,
                refund_data
            )
            
            return {
                'success': response is not None,
                'refund_id': response.get('refund', {}).get('id') if response else None,
                'message': 'Refund processed' if response else 'Failed to process refund'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order status in Shopify"""
        try:
            # Shopify uses tags for custom status
            headers = {'X-Shopify-Access-Token': self.access_token}
            order_data = {
                'order': {
                    'tags': f'return-{status}'
                }
            }
            
            response = self._make_request(
                'PUT',
                f'/orders/{order_id}.json',
                headers,
                order_data
            )
            
            return response is not None
        except Exception as e:
            print(f"Error updating Shopify order: {e}")
            return False
    
    def _convert_shopify_order(self, shopify_order: Dict) -> Order:
        """Convert Shopify order to universal Order model"""
        return Order(
            order_id=str(shopify_order.get('id')),
            platform='shopify',
            customer_id=str(shopify_order.get('customer', {}).get('id')),
            customer_email=shopify_order.get('customer', {}).get('email', ''),
            customer_name=shopify_order.get('customer', {}).get('display_name', 'Customer'),
            order_date=datetime.fromisoformat(shopify_order.get('created_at', '').replace('Z', '+00:00')),
            items=[
                {
                    'id': item.get('id'),
                    'name': item.get('title'),
                    'sku': item.get('sku'),
                    'quantity': item.get('quantity'),
                    'price': float(item.get('price', 0))
                }
                for item in shopify_order.get('line_items', [])
            ],
            total_amount=float(shopify_order.get('total_price', 0)),
            currency=shopify_order.get('currency', 'USD'),
            shipping_address={
                'address': shopify_order.get('shipping_address', {}).get('address1'),
                'city': shopify_order.get('shipping_address', {}).get('city'),
                'zip': shopify_order.get('shipping_address', {}).get('zip'),
                'country': shopify_order.get('shipping_address', {}).get('country')
            }
        )
    
    def _make_request(self, method: str, endpoint: str, headers: Dict, 
                     data: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request to Shopify API"""
        import requests
        
        url = f"{self.base_url}{endpoint}"
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            else:
                return None
            
            if response.status_code in [200, 201]:
                return response.json()
            return None
        except Exception as e:
            print(f"Request failed: {e}")
            return None


class WooCommerceConnector(PlatformConnector):
    """WooCommerce API connector"""
    
    def __init__(self, api_key: str, store_url: str, consumer_key: str, consumer_secret: str):
        super().__init__(api_key, store_url)
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.base_url = f"https://{store_url}/wp-json/wc/v3"
    
    def authenticate(self) -> bool:
        """Verify WooCommerce API credentials"""
        try:
            response = self._make_request('GET', '/system/status')
            return response is not None
        except Exception as e:
            print(f"WooCommerce authentication failed: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get WooCommerce order by ID"""
        try:
            response = self._make_request('GET', f'/orders/{order_id}')
            
            if response:
                return self._convert_woo_order(response)
            return None
        except Exception as e:
            print(f"Error fetching WooCommerce order: {e}")
            return None
    
    def get_orders(self, customer_id: str) -> List[Order]:
        """Get all WooCommerce orders for customer"""
        try:
            response = self._make_request('GET', '/orders', {'customer': customer_id})
            
            if isinstance(response, list):
                return [self._convert_woo_order(o) for o in response]
            return []
        except Exception as e:
            print(f"Error fetching WooCommerce orders: {e}")
            return []
    
    def create_refund(self, order_id: str, amount: float, reason: str) -> Dict:
        """Create refund in WooCommerce"""
        try:
            refund_data = {
                'amount': str(amount),
                'reason': reason
            }
            
            response = self._make_request(
                'POST',
                f'/orders/{order_id}/refunds',
                refund_data
            )
            
            return {
                'success': response is not None,
                'refund_id': response.get('id') if response else None,
                'message': 'Refund processed' if response else 'Failed to process refund'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order status in WooCommerce"""
        try:
            order_data = {'status': status}
            response = self._make_request('PUT', f'/orders/{order_id}', order_data)
            return response is not None
        except Exception as e:
            print(f"Error updating WooCommerce order: {e}")
            return False
    
    def _convert_woo_order(self, woo_order: Dict) -> Order:
        """Convert WooCommerce order to universal Order model"""
        return Order(
            order_id=str(woo_order.get('id')),
            platform='woocommerce',
            customer_id=str(woo_order.get('customer_id')),
            customer_email=woo_order.get('billing', {}).get('email', ''),
            customer_name=woo_order.get('billing', {}).get('first_name', '') + ' ' + 
                         woo_order.get('billing', {}).get('last_name', ''),
            order_date=datetime.fromisoformat(woo_order.get('date_created', '').split('+')[0]),
            items=[
                {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'sku': item.get('sku'),
                    'quantity': item.get('quantity'),
                    'price': float(item.get('price', 0))
                }
                for item in woo_order.get('line_items', [])
            ],
            total_amount=float(woo_order.get('total', 0)),
            currency=woo_order.get('currency', 'USD'),
            shipping_address={
                'address': woo_order.get('shipping', {}).get('address_1'),
                'city': woo_order.get('shipping', {}).get('city'),
                'zip': woo_order.get('shipping', {}).get('postcode'),
                'country': woo_order.get('shipping', {}).get('country')
            }
        )
    
    def _make_request(self, method: str, endpoint: str, 
                     data: Optional[Dict] = None, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make OAuth-signed request to WooCommerce API"""
        from requests_oauthlib import OAuth1Session
        
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            signature_type='QUERY'
        )
        
        url = f"{self.base_url}{endpoint}"
        try:
            if method == 'GET':
                response = oauth.get(url, params=params, timeout=10)
            elif method == 'POST':
                response = oauth.post(url, json=data, timeout=10)
            elif method == 'PUT':
                response = oauth.put(url, json=data, timeout=10)
            else:
                return None
            
            if response.status_code in [200, 201]:
                return response.json()
            return None
        except Exception as e:
            print(f"Request failed: {e}")
            return None


class PlatformFactory:
    """Factory for creating platform connectors"""
    
    _connectors = {
        'shopify': ShopifyConnector,
        'woocommerce': WooCommerceConnector,
    }
    
    @staticmethod
    def create(platform: str, **kwargs) -> Optional[PlatformConnector]:
        """Create connector for specified platform"""
        ConnectorClass = PlatformFactory._connectors.get(platform.lower())
        if ConnectorClass:
            return ConnectorClass(**kwargs)
        raise ValueError(f"Unsupported platform: {platform}")
