"""
Return Label Generator
Generates shipping labels with barcodes, QR codes, and tracking
"""

import qrcode
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from datetime import datetime, timedelta
import uuid
import json
from dataclasses import dataclass, asdict


@dataclass
class LabelConfig:
    """Label generation configuration"""
    carrier: str  # 'fedex', 'ups', 'usps', 'dhl'
    service_type: str  # 'ground', 'express', 'overnight'
    from_address: dict  # Warehouse address
    to_address: dict  # Customer address
    weight_lbs: float
    dimensions: dict  # {'length': x, 'width': y, 'height': z}


class ReturnLabelGenerator:
    """Generates return shipping labels"""
    
    CARRIERS = {
        'fedex': {'name': 'FedEx', 'prefix': 'FX'},
        'ups': {'name': 'UPS', 'prefix': 'UP'},
        'usps': {'name': 'USPS', 'prefix': 'US'},
        'dhl': {'name': 'DHL', 'prefix': 'DH'}
    }
    
    def __init__(self, api_keys: dict = None):
        """
        Initialize label generator
        
        Args:
            api_keys: Dict with carrier API keys {
                'fedex': 'key',
                'ups': 'key',
                'usps': 'key',
                'dhl': 'key'
            }
        """
        self.api_keys = api_keys or {}
        self.carrier_costs = {
            'fedex': {'ground': 8.50, 'express': 15.00, 'overnight': 25.00},
            'ups': {'ground': 7.95, 'express': 14.50, 'overnight': 22.00},
            'usps': {'ground': 4.50, 'express': 8.00, 'overnight': 18.00},
            'dhl': {'ground': 9.00, 'express': 16.00, 'overnight': 26.00}
        }
    
    def generate_label(self, return_id: str, config: LabelConfig) -> dict:
        """
        Generate return shipping label
        
        Args:
            return_id: Return request ID
            config: Label configuration
            
        Returns:
            Label data with tracking number, QR code, barcode
        """
        try:
            # Generate tracking number
            tracking_number = self._generate_tracking_number(
                config.carrier,
                return_id
            )
            
            # Generate QR code
            qr_code_data = self._generate_qr_code(tracking_number)
            
            # Generate barcode
            barcode_data = self._generate_barcode(tracking_number)
            
            # Calculate delivery estimate
            estimated_delivery = self._estimate_delivery(
                config.carrier,
                config.service_type
            )
            
            # Get shipping cost
            shipping_cost = self._get_shipping_cost(
                config.carrier,
                config.service_type,
                config.weight_lbs
            )
            
            label_id = f"lbl_{uuid.uuid4().hex[:8]}"
            
            return {
                'success': True,
                'label_id': label_id,
                'tracking_number': tracking_number,
                'carrier': config.carrier.upper(),
                'service_type': config.service_type,
                'qr_code': qr_code_data,
                'barcode': barcode_data,
                'shipping_cost': shipping_cost,
                'estimated_delivery': estimated_delivery.isoformat(),
                'created_at': datetime.now().isoformat(),
                'label_data': {
                    'from_address': config.from_address,
                    'to_address': config.to_address,
                    'weight': config.weight_lbs,
                    'dimensions': config.dimensions
                }
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_tracking_number(self, carrier: str, return_id: str) -> str:
        """Generate carrier-specific tracking number"""
        prefix = self.CARRIERS.get(carrier.lower(), {}).get('prefix', 'TR')
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        return_hash = return_id[-8:].upper()
        tracking = f"{prefix}{timestamp}{return_hash}"
        return tracking
    
    def _generate_qr_code(self, tracking_number: str) -> str:
        """Generate QR code for tracking"""
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(tracking_number)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            import base64
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            qr_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{qr_b64}"
        except Exception as e:
            print(f"QR code generation error: {e}")
            return ""
    
    def _generate_barcode(self, tracking_number: str) -> str:
        """Generate barcode for tracking"""
        try:
            # Use CODE128 format
            barcode_obj = barcode.get('code128', tracking_number, writer=ImageWriter())
            
            buffer = BytesIO()
            barcode_obj.write(buffer)
            buffer.seek(0)
            
            import base64
            barcode_b64 = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{barcode_b64}"
        except Exception as e:
            print(f"Barcode generation error: {e}")
            return ""
    
    def _estimate_delivery(self, carrier: str, service_type: str) -> datetime:
        """Estimate delivery date"""
        days_map = {
            'ground': 5,
            'express': 3,
            'overnight': 1
        }
        days = days_map.get(service_type, 5)
        return datetime.now() + timedelta(days=days)
    
    def _get_shipping_cost(self, carrier: str, service_type: str, weight_lbs: float) -> float:
        """Calculate shipping cost"""
        base_cost = self.carrier_costs.get(carrier.lower(), {}).get(service_type, 5.0)
        weight_surcharge = max(0, (weight_lbs - 1)) * 0.50
        return round(base_cost + weight_surcharge, 2)
    
    def generate_bulk_labels(self, return_ids: list, config: LabelConfig) -> list:
        """Generate multiple labels"""
        labels = []
        for return_id in return_ids:
            label = self.generate_label(return_id, config)
            labels.append(label)
        return labels
    
    def validate_address(self, address: dict) -> bool:
        """Validate shipping address"""
        required_fields = ['street', 'city', 'state', 'zip', 'country']
        return all(field in address and address[field] for field in required_fields)
    
    def format_label_for_print(self, label_data: dict) -> str:
        """Format label for thermal printer"""
        if not label_data.get('success'):
            return "Error generating label"
        
        template = f"""
╔══════════════════════════════════════════╗
║        RETURN SHIPPING LABEL             ║
╠══════════════════════════════════════════╣
║                                          ║
║  Carrier: {label_data['carrier']:<30} ║
║  Tracking: {label_data['tracking_number']:<24} ║
║  Service: {label_data['service_type']:<30} ║
║                                          ║
║  Cost: ${label_data['shipping_cost']:<33} ║
║  Est. Delivery: {label_data['estimated_delivery']:<20} ║
║                                          ║
╠══════════════════════════════════════════╣
║                                          ║
║  FROM:                                   ║
║  {label_data['label_data']['from_address']['name']:<40} ║
║  {label_data['label_data']['from_address']['address']:<40} ║
║  {label_data['label_data']['from_address']['city']}, {label_data['label_data']['from_address']['state']} {label_data['label_data']['from_address']['zip']:<20} ║
║                                          ║
║  TO:                                     ║
║  {label_data['label_data']['to_address']['name']:<40} ║
║  {label_data['label_data']['to_address']['address']:<40} ║
║  {label_data['label_data']['to_address']['city']}, {label_data['label_data']['to_address']['state']} {label_data['label_data']['to_address']['zip']:<20} ║
║                                          ║
╚══════════════════════════════════════════╝
        """
        return template
