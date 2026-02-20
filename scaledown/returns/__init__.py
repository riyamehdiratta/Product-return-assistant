"""
E-Commerce Returns Assistant Module

Simplified and automated product returns using compressed return policies 
and product-aware reasoning.
"""

from scaledown.returns.policy_compressor import PolicyCompressor
from scaledown.returns.eligibility_engine import EligibilityEngine, EligibilityResult
from scaledown.returns.conversation_handler import ConversationHandler
from scaledown.returns.types import (
    ReturnPolicy,
    Product,
    ReturnRequest,
    ConversationContext,
    ReturnReason,
    RefundStatus,
    ReturnStatus,
    ReturnAnalytics
)
from scaledown.returns.platform_connectors import (
    PlatformConnector,
    ShopifyConnector,
    WooCommerceConnector,
    PlatformFactory,
    Order
)
from scaledown.returns.label_generator import ReturnLabelGenerator, LabelConfig
from scaledown.returns.metrics_tracker import MetricsTracker

__all__ = [
    "PolicyCompressor",
    "EligibilityEngine",
    "EligibilityResult",
    "ConversationHandler",
    "ReturnPolicy",
    "Product",
    "ReturnRequest",
    "ConversationContext",
    "ReturnReason",
    "RefundStatus",
    "ReturnStatus",
    "ReturnAnalytics",
]
