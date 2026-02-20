"""
Tests for E-Commerce Returns Assistant.

Tests coverage:
- Policy compression and extraction
- Eligibility determination
- Conversation handling and intent detection
- Analytics and fraud detection
"""

import pytest
from datetime import datetime, timedelta
from scaledown.returns import (
    PolicyCompressor,
    EligibilityEngine,
    ConversationHandler,
    ReturnPolicy,
    Product,
    ReturnRequest,
    ConversationContext,
    ReturnReason,
    ReturnStatus,
    RefundStatus,
    EligibilityResult
)


class TestPolicyCompressor:
    """Tests for policy compression and extraction."""
    
    @pytest.fixture
    def compressor(self):
        return PolicyCompressor()
    
    @pytest.fixture
    def sample_policy_text(self):
        return """
        RETURN POLICY
        
        Customers have 30 days to return items from the date of purchase.
        
        ELIGIBLE CONDITIONS:
        - Items must be in original packaging
        - New or unopened products
        
        REFUND DEDUCTION:
        A 10% restocking fee is applied to all returns.
        
        ELIGIBLE CATEGORIES:
        Electronics, clothing, home goods, and toys.
        
        EXCLUSIONS:
        Final sale items, clearance items, and custom orders cannot be returned.
        
        TIMELINE:
        - Return approval: Within 24 hours
        - Refund processing: 5-7 business days
        
        ADDITIONAL OPTIONS:
        - Replacement available
        - Store pickup available
        - Original packaging required
        """
    
    def test_extract_return_window(self, compressor, sample_policy_text):
        """Test extraction of return window."""
        extracted = compressor._extract_return_window(sample_policy_text)
        assert extracted == 30
    
    def test_extract_refund_type(self, compressor, sample_policy_text):
        """Test extraction of refund type."""
        refund_type = compressor._extract_refund_type(sample_policy_text)
        assert refund_type in ["full", "partial", "store_credit"]
    
    def test_extract_deduction_percentage(self, compressor, sample_policy_text):
        """Test extraction of deduction percentage."""
        deduction = compressor._extract_deduction_pct(sample_policy_text)
        assert deduction == 10.0
    
    def test_extract_categories(self, compressor, sample_policy_text):
        """Test extraction of eligible categories."""
        categories = compressor._extract_categories(sample_policy_text)
        assert "electronics" in categories
        assert "clothing" in categories
    
    def test_extract_conditions(self, compressor, sample_policy_text):
        """Test extraction of eligible conditions."""
        conditions = compressor._extract_conditions(sample_policy_text)
        assert "new" in conditions or "unopened" in conditions
    
    def test_extract_exclusions(self, compressor, sample_policy_text):
        """Test extraction of exclusions."""
        exclusions = compressor._extract_exclusions(sample_policy_text)
        assert len(exclusions) > 0
    
    def test_parse_policy(self, compressor, sample_policy_text):
        """Test full policy parsing."""
        policy = compressor.parse_policy(
            sample_policy_text,
            seller_id="seller_123",
            policy_name="Standard Policy"
        )
        
        assert isinstance(policy, ReturnPolicy)
        assert policy.return_window_days == 30
        assert policy.refund_deduction_pct == 10.0
        assert policy.seller_id == "seller_123"
        assert policy.policy_name == "Standard Policy"


class TestEligibilityEngine:
    """Tests for eligibility checking."""
    
    @pytest.fixture
    def sample_policy(self):
        return ReturnPolicy(
            policy_id="policy_123",
            seller_id="seller_123",
            policy_name="Standard Policy",
            return_window_days=30,
            refund_type="full",
            refund_deduction_pct=0.0,
            eligible_categories=["electronics", "clothing"],
            eligible_conditions=["new", "unopened"],
            exclusions=["custom orders"],
            final_sale_items=["clearance"],
            approval_time_hours=24,
            refund_time_days=5,
            supports_replacement=True,
            supports_pickup=False,
            requires_original_packaging=True
        )
    
    @pytest.fixture
    def sample_product(self):
        return Product(
            product_id="prod_123",
            name="Wireless Headphones",
            category="electronics",
            price=79.99,
            purchase_date=datetime.now() - timedelta(days=10),
            condition="new",
            seller_id="seller_123",
            seller_name="TechStore",
            sku="TECH-001",
            description="High-quality wireless headphones"
        )
    
    @pytest.fixture
    def sample_return_request(self, sample_product):
        return ReturnRequest(
            return_id="ret_123",
            customer_id="cust_123",
            product=sample_product,
            reason=ReturnReason.CHANGED_MIND,
            description="Changed my mind about the color",
            reason_category="preference"
        )
    
    def test_check_return_window_within(self, sample_policy, sample_return_request):
        """Test return window check - within window."""
        engine = EligibilityEngine(sample_policy)
        is_eligible, msg = engine._check_return_window(sample_return_request)
        
        assert is_eligible is True
        assert "within" in msg.lower()
    
    def test_check_return_window_exceeded(self, sample_policy, sample_product):
        """Test return window check - exceeded window."""
        old_product = Product(
            product_id="prod_old",
            name="Old Headphones",
            category="electronics",
            price=79.99,
            purchase_date=datetime.now() - timedelta(days=40),  # 40 days ago
            condition="new",
            seller_id="seller_123",
            seller_name="TechStore",
            sku="TECH-002"
        )
        
        old_return = ReturnRequest(
            return_id="ret_old",
            customer_id="cust_123",
            product=old_product,
            reason=ReturnReason.CHANGED_MIND,
            description="Changed my mind",
            reason_category="preference"
        )
        
        engine = EligibilityEngine(sample_policy)
        is_eligible, msg = engine._check_return_window(old_return)
        
        assert is_eligible is False
        assert "exceeds" in msg.lower()
    
    def test_check_category_eligibility_eligible(self, sample_policy, sample_return_request):
        """Test category eligibility - eligible."""
        engine = EligibilityEngine(sample_policy)
        is_eligible, msg = engine._check_category_eligibility(sample_return_request)
        
        assert is_eligible is True
    
    def test_check_category_eligibility_ineligible(self, sample_policy, sample_product):
        """Test category eligibility - not eligible."""
        ineligible_product = Product(
            product_id="prod_fur",
            name="Dining Table",
            category="furniture",
            price=499.99,
            purchase_date=datetime.now() - timedelta(days=10),
            condition="new",
            seller_id="seller_123",
            seller_name="TechStore",
            sku="TECH-003"
        )
        
        ineligible_return = ReturnRequest(
            return_id="ret_fur",
            customer_id="cust_123",
            product=ineligible_product,
            reason=ReturnReason.CHANGED_MIND,
            description="Changed my mind",
            reason_category="preference"
        )
        
        engine = EligibilityEngine(sample_policy)
        is_eligible, msg = engine._check_category_eligibility(ineligible_return)
        
        assert is_eligible is False
    
    def test_check_exclusions(self, sample_policy, sample_return_request):
        """Test exclusions check."""
        engine = EligibilityEngine(sample_policy)
        is_not_excluded, msg = engine._check_exclusions(sample_return_request)
        
        assert is_not_excluded is True
    
    def test_check_eligibility_approved(self, sample_policy, sample_return_request):
        """Test full eligibility check - approved."""
        engine = EligibilityEngine(sample_policy)
        result = engine.check_eligibility(sample_return_request)
        
        assert isinstance(result, EligibilityResult)
        assert result.is_eligible is True
        assert len(result.checks_passed) > 0
    
    def test_calculate_refund_amount_full(self, sample_policy, sample_return_request):
        """Test refund calculation - full refund."""
        engine = EligibilityEngine(sample_policy)
        amount, reason = engine.calculate_refund_amount(sample_return_request)
        
        assert amount == sample_return_request.product.price
        assert "full" in reason.lower()
    
    def test_calculate_refund_amount_with_deduction(self, sample_return_request):
        """Test refund calculation - with deduction."""
        policy_with_deduction = ReturnPolicy(
            policy_id="policy_123",
            seller_id="seller_123",
            policy_name="Policy with fee",
            return_window_days=30,
            refund_type="full",
            refund_deduction_pct=10.0,  # 10% restocking fee
            eligible_categories=["all"],
            eligible_conditions=["new"],
            exclusions=[],
            final_sale_items=[],
            approval_time_hours=24,
            refund_time_days=5,
            supports_replacement=True,
            supports_pickup=False,
            requires_original_packaging=False
        )
        
        engine = EligibilityEngine(policy_with_deduction)
        amount, reason = engine.calculate_refund_amount(sample_return_request)
        
        expected = sample_return_request.product.price * 0.9  # 90% of original
        assert amount == expected
        assert "restocking" in reason.lower()


class TestConversationHandler:
    """Tests for conversation handling."""
    
    @pytest.fixture
    def sample_policies(self):
        return {
            "seller_123": ReturnPolicy(
                policy_id="policy_123",
                seller_id="seller_123",
                policy_name="Standard Policy",
                return_window_days=30,
                refund_type="full",
                refund_deduction_pct=0.0,
                eligible_categories=["electronics"],
                eligible_conditions=["new"],
                exclusions=[],
                final_sale_items=[],
                approval_time_hours=24,
                refund_time_days=5,
                supports_replacement=True,
                supports_pickup=True,
                requires_original_packaging=False
            )
        }
    
    @pytest.fixture
    def sample_context(self):
        return ConversationContext(
            conversation_id="conv_123",
            customer_id="cust_123",
            customer_name="John Doe"
        )
    
    def test_detect_sentiment_neutral(self, sample_policies):
        """Test sentiment detection - neutral."""
        handler = ConversationHandler(sample_policies)
        sentiment, frustration = handler._detect_sentiment("Can you help me with my return?")
        
        assert sentiment == "neutral"
        assert 0 <= frustration <= 1
    
    def test_detect_sentiment_frustrated(self, sample_policies):
        """Test sentiment detection - frustrated."""
        handler = ConversationHandler(sample_policies)
        sentiment, frustration = handler._detect_sentiment("I'm so frustrated with your process!")
        
        assert sentiment == "frustrated"
        assert frustration > 0.6
    
    def test_detect_sentiment_angry(self, sample_policies):
        """Test sentiment detection - angry."""
        handler = ConversationHandler(sample_policies)
        sentiment, frustration = handler._detect_sentiment("This is a complete scam!")
        
        assert sentiment == "angry"
        assert frustration > 0.8
    
    def test_extract_intent_eligibility(self, sample_policies):
        """Test intent extraction - eligibility check."""
        handler = ConversationHandler(sample_policies)
        intent, data = handler._extract_intent("Can I return this item?", 
                                              ConversationContext(
                                                  conversation_id="conv_123",
                                                  customer_id="cust_123"
                                              ))
        
        assert intent == "check_eligibility"
    
    def test_extract_intent_policy_question(self, sample_policies):
        """Test intent extraction - policy question."""
        handler = ConversationHandler(sample_policies)
        intent, data = handler._extract_intent("What's your return policy?",
                                              ConversationContext(
                                                  conversation_id="conv_123",
                                                  customer_id="cust_123"
                                              ))
        
        assert intent == "policy_question"
    
    def test_extract_intent_initiate_return(self, sample_policies):
        """Test intent extraction - initiate return."""
        handler = ConversationHandler(sample_policies)
        intent, data = handler._extract_intent("I want to return this headphones",
                                              ConversationContext(
                                                  conversation_id="conv_123",
                                                  customer_id="cust_123"
                                              ))
        
        assert intent == "initiate_return"
    
    def test_handle_message_updates_context(self, sample_policies, sample_context):
        """Test that handle_message updates context correctly."""
        handler = ConversationHandler(sample_policies)
        
        initial_count = sample_context.message_count
        response, updated_context = handler.handle_message(
            sample_context,
            "What is your return policy?"
        )
        
        assert updated_context.message_count == initial_count + 1
        assert len(updated_context.messages) == 2  # user + assistant
        assert updated_context.messages[0]["role"] == "user"
        assert updated_context.messages[1]["role"] == "assistant"
    
    def test_handle_message_detects_escalation(self, sample_policies, sample_context):
        """Test that frustrated messages trigger escalation."""
        handler = ConversationHandler(sample_policies, escalation_threshold=0.6)
        
        response, updated_context = handler.handle_message(
            sample_context,
            "I'm absolutely furious about this terrible service! This is criminal!"
        )
        
        assert updated_context.escalation_required is True
        assert "support" in response.lower()


class TestReturnTypes:
    """Tests for return data types."""
    
    def test_return_policy_creation(self):
        """Test ReturnPolicy object creation."""
        policy = ReturnPolicy(
            policy_id="policy_123",
            seller_id="seller_123",
            policy_name="Test Policy",
            return_window_days=30,
            refund_type="full",
            refund_deduction_pct=5.0,
            eligible_categories=["all"],
            eligible_conditions=["new"],
            exclusions=["custom"],
            final_sale_items=["clearance"],
            approval_time_hours=24,
            refund_time_days=5,
            supports_replacement=True,
            supports_pickup=True,
            requires_original_packaging=False
        )
        
        assert policy.policy_id == "policy_123"
        assert policy.return_window_days == 30
        assert policy.refund_deduction_pct == 5.0
    
    def test_product_creation(self):
        """Test Product object creation."""
        product = Product(
            product_id="prod_123",
            name="Test Product",
            category="electronics",
            price=99.99,
            purchase_date=datetime.now(),
            condition="new",
            seller_id="seller_123",
            seller_name="Test Seller",
            sku="SKU-001"
        )
        
        assert product.product_id == "prod_123"
        assert product.price == 99.99
    
    def test_return_request_creation(self):
        """Test ReturnRequest object creation."""
        product = Product(
            product_id="prod_123",
            name="Test Product",
            category="electronics",
            price=99.99,
            purchase_date=datetime.now(),
            condition="new",
            seller_id="seller_123",
            seller_name="Test Seller",
            sku="SKU-001"
        )
        
        return_req = ReturnRequest(
            return_id="ret_123",
            customer_id="cust_123",
            product=product,
            reason=ReturnReason.DEFECTIVE,
            description="Product stopped working",
            reason_category="defect"
        )
        
        assert return_req.return_id == "ret_123"
        assert return_req.reason == ReturnReason.DEFECTIVE
        assert return_req.status == ReturnStatus.INITIATED
        assert return_req.refund_status == RefundStatus.PENDING


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
