"""
Data types and models for the E-Commerce Returns Assistant.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum


class ReturnReason(Enum):
    """Enumeration of possible return reasons."""
    DEFECTIVE = "defective"
    DAMAGED = "damaged_in_transit"
    NOT_AS_DESCRIBED = "not_as_described"
    WRONG_ITEM = "wrong_item"
    CHANGED_MIND = "changed_mind"
    TOO_SMALL = "too_small"
    TOO_LARGE = "too_large"
    OTHER = "other"


class RefundStatus(Enum):
    """Enumeration of refund statuses."""
    PENDING = "pending"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"


class ReturnStatus(Enum):
    """Enumeration of return statuses."""
    INITIATED = "initiated"
    LABEL_GENERATED = "label_generated"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    INSPECTING = "inspecting"
    APPROVED = "approved"
    REJECTED = "rejected"
    REFUNDED = "refunded"


@dataclass
class ReturnPolicy:
    """Represents a compressed return policy with actionable rules."""
    
    policy_id: str
    seller_id: str
    policy_name: str
    
    # Core rules (compressed)
    return_window_days: int  # How many days to return
    refund_type: str  # "full", "partial", "store_credit"
    refund_deduction_pct: float  # Percentage deduction (e.g., 10% for restocking)
    
    # Eligibility rules
    eligible_categories: List[str]  # Product categories eligible for return
    eligible_conditions: List[str]  # Conditions: "new", "unopened", "gently_used"
    
    # Exclusions
    exclusions: List[str]  # Non-returnable items
    final_sale_items: List[str]  # Final sale categories
    
    # Timeline
    approval_time_hours: int  # How long to approve a return
    refund_time_days: int  # How long to process refund
    
    # Features
    supports_replacement: bool
    supports_pickup: bool
    requires_original_packaging: bool
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    original_policy_tokens: int = 0  # Original policy token count
    compressed_policy_tokens: int = 0  # Compressed policy token count
    original_policy_text: str = ""  # Store raw policy for reference


@dataclass
class Product:
    """Represents a product being returned."""
    
    product_id: str
    name: str
    category: str
    price: float
    purchase_date: datetime
    condition: str  # "new", "unopened", "gently_used", "damaged"
    seller_id: str
    seller_name: str
    sku: str
    description: str = ""


@dataclass
class ReturnRequest:
    """Represents a return request initiated by a customer."""
    
    return_id: str
    customer_id: str
    product: Product
    reason: ReturnReason
    description: str
    reason_category: str  # extracted high-level category
    
    # Status tracking
    status: ReturnStatus = ReturnStatus.INITIATED
    refund_status: RefundStatus = RefundStatus.PENDING
    
    # Eligibility
    is_eligible: bool = False
    eligibility_reason: str = ""  # Explanation for eligibility decision
    
    # Exchange support
    exchange_requested: bool = False
    exchange_product_id: Optional[str] = None
    exchange_product_name: Optional[str] = None
    
    # Tracking
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    return_label_url: Optional[str] = None
    tracking_number: Optional[str] = None
    pickup_scheduled_at: Optional[datetime] = None
    received_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    
    # Refund details
    refund_amount: float = 0.0
    deduction_reason: str = ""  # Why deductions were made
    
    # Additional metadata
    fraud_score: float = 0.0  # 0-1 scale for potential fraud
    is_flagged: bool = False
    flag_reason: str = ""


@dataclass
class ConversationContext:
    """Context for a conversation with the customer."""
    
    conversation_id: str
    customer_id: str
    customer_name: str = ""
    customer_sentiment: str = "neutral"  # "satisfied", "neutral", "frustrated", "angry"
    frustration_level: float = 0.0  # 0-1 scale
    
    # Conversation history
    messages: List[Dict[str, str]] = field(default_factory=list)  # [{"role": "user|assistant", "content": "..."}]
    
    # Current context
    current_return_request: Optional[ReturnRequest] = None
    product_context: Optional[Product] = None
    policy_context: Optional[ReturnPolicy] = None
    
    # Analytics
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    escalation_required: bool = False
    escalation_reason: str = ""


@dataclass
class EligibilityResult:
    """Result of eligibility check for a return request."""
    
    is_eligible: bool
    reasons: List[str]  # Detailed reasons for decision
    warnings: List[str] = field(default_factory=list)  # Non-blocking warnings
    suggestions: List[str] = field(default_factory=list)  # Alternative solutions
    
    # Step-by-step breakdown
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)


@dataclass
class ReturnAnalytics:
    """Analytics about returns and policies."""
    
    total_returns: int
    total_approved: int
    total_rejected: int
    
    top_return_reasons: Dict[str, int]  # reason -> count
    top_returned_products: List[str]  # product names
    policy_confusion_points: Dict[str, int]  # policy section -> confusion count
    
    avg_refund_amount: float
    avg_processing_days: float
    estimated_monthly_savings: float  # From automated handling
    
    fraud_flags: int
    high_return_customers: List[str]
