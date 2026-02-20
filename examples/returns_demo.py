"""
E-Commerce Returns Assistant - Demo & Examples

This example demonstrates how to use the ScaleDown-powered Returns Assistant
for compressing policies, checking eligibility, and handling conversations.
"""

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
)


# ============================================================================
# Example 1: Policy Compression
# ============================================================================

def example_policy_compression():
    """Demonstrate policy compression from raw text."""
    
    print("=" * 70)
    print("EXAMPLE 1: Policy Compression")
    print("=" * 70)
    
    # Raw policy text (typically from PDF or website)
    raw_policy = """
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
    
    # Create compressor
    compressor = PolicyCompressor()
    
    # Parse and compress policy
    print("\n📄 Original policy length: ~", len(raw_policy), "characters")
    
    policy = compressor.parse_policy(
        policy_text=raw_policy,
        seller_id="seller_electronics_001",
        policy_name="Electronics Return Policy"
    )
    
    print(f"✅ Policy compressed!")
    print(f"\n📋 Extracted Policy Rules:")
    print(f"  • Return Window: {policy.return_window_days} days")
    print(f"  • Refund Type: {policy.refund_type.upper()}")
    print(f"  • Restocking Fee: {policy.refund_deduction_pct}%")
    print(f"  • Eligible Categories: {', '.join(policy.eligible_categories)}")
    print(f"  • Approval Time: {policy.approval_time_hours} hours")
    print(f"  • Refund Processing: {policy.refund_time_days} business days")
    print(f"  • Supports Replacement: {'✅ Yes' if policy.supports_replacement else '❌ No'}")
    print(f"  • Supports Pickup: {'✅ Yes' if policy.supports_pickup else '❌ No'}")
    
    return policy


# ============================================================================
# Example 2: Eligibility Checking
# ============================================================================

def example_eligibility_checking(policy):
    """Demonstrate eligibility checking with detailed reasoning."""
    
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Eligibility Checking")
    print("=" * 70)
    
    # Create a product
    product = Product(
        product_id="prod_gaming_laptop_001",
        name="Gaming Laptop Pro X1",
        category="electronics",
        price=1299.99,
        purchase_date=datetime.now() - timedelta(days=15),  # 15 days ago
        condition="unopened",
        seller_id="seller_electronics_001",
        seller_name="TechStore Electronics",
        sku="TECH-LAPTOP-001",
        description="High-performance gaming laptop"
    )
    
    # Create a return request
    return_request = ReturnRequest(
        return_id="ret_001",
        customer_id="cust_123",
        product=product,
        reason=ReturnReason.CHANGED_MIND,
        description="Found a better deal elsewhere",
        reason_category="preference"
    )
    
    print(f"\n📦 Return Request:")
    print(f"  Product: {product.name}")
    print(f"  Price: ${product.price:.2f}")
    print(f"  Days Since Purchase: {(datetime.now() - product.purchase_date).days}")
    print(f"  Condition: {product.condition}")
    print(f"  Reason: {return_request.reason.value}")
    
    # Check eligibility
    engine = EligibilityEngine(policy)
    result = engine.check_eligibility(return_request)
    
    print(f"\n✅ Eligibility Result: {'APPROVED' if result.is_eligible else 'REJECTED'}")
    
    if result.is_eligible:
        print(f"\n✓ Checks Passed:")
        for check in result.checks_passed:
            print(f"  ✓ {check}")
    else:
        print(f"\n✗ Checks Failed:")
        for check in result.checks_failed:
            print(f"  ✗ {check}")
    
    if result.reasons:
        print(f"\n📝 Detailed Reasons:")
        for reason in result.reasons:
            print(f"  • {reason}")
    
    if result.suggestions:
        print(f"\n💡 Suggestions:")
        for suggestion in result.suggestions:
            print(f"  • {suggestion}")
    
    # Calculate refund
    refund_amount, deduction_reason = engine.calculate_refund_amount(return_request)
    print(f"\n💰 Refund Amount: ${refund_amount:.2f}")
    print(f"   ({deduction_reason})")
    
    return_request.refund_amount = refund_amount
    return return_request


# ============================================================================
# Example 3: Conversation Handling
# ============================================================================

def example_conversation_handling(policy, return_request):
    """Demonstrate natural language conversation handling."""
    
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Conversation Handling")
    print("=" * 70)
    
    # Create conversation context
    context = ConversationContext(
        conversation_id="conv_001",
        customer_id="cust_123",
        customer_name="Alice Johnson",
        policy_context=policy,
        current_return_request=return_request
    )
    
    # Create handler
    handler = ConversationHandler({"seller_electronics_001": policy})
    
    # Example conversation
    messages = [
        "Hi, I'd like to return my laptop",
        "Is my return eligible? I bought it 15 days ago",
        "Can I get a replacement instead of a refund?",
        "When will I get my money back?",
    ]
    
    print(f"\n💬 Starting Conversation with {context.customer_name}:\n")
    
    for msg in messages:
        print(f"Customer: {msg}")
        response, context = handler.handle_message(context, msg)
        print(f"Assistant: {response}\n")
        print("-" * 70 + "\n")


# ============================================================================
# Example 4: Complex Scenario - Ineligible Return
# ============================================================================

def example_ineligible_return(policy):
    """Demonstrate handling of ineligible returns."""
    
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Ineligible Return Handling")
    print("=" * 70)
    
    # Product purchased too long ago
    old_product = Product(
        product_id="prod_old_phone",
        name="Used Smartphone",
        category="electronics",
        price=399.99,
        purchase_date=datetime.now() - timedelta(days=45),  # 45 days ago (outside 30-day window)
        condition="heavily_used",
        seller_id="seller_electronics_001",
        seller_name="TechStore Electronics",
        sku="TECH-PHONE-OLD"
    )
    
    old_return = ReturnRequest(
        return_id="ret_002",
        customer_id="cust_456",
        product=old_product,
        reason=ReturnReason.NOT_AS_DESCRIBED,
        description="Phone specs don't match listing",
        reason_category="mismatch"
    )
    
    print(f"\n📦 Return Request:")
    print(f"  Product: {old_product.name}")
    print(f"  Purchase Date: {old_product.purchase_date.strftime('%Y-%m-%d')}")
    print(f"  Days Elapsed: {(datetime.now() - old_product.purchase_date).days}")
    print(f"  Policy Return Window: {policy.return_window_days} days")
    
    engine = EligibilityEngine(policy)
    result = engine.check_eligibility(old_return)
    
    print(f"\n❌ Eligibility Result: REJECTED")
    print(f"\nReasons:")
    for reason in result.reasons:
        print(f"  • {reason}")
    
    print(f"\nAlternatives:")
    for suggestion in result.suggestions:
        print(f"  • {suggestion}")


# ============================================================================
# Example 5: Fraud Detection
# ============================================================================

def example_fraud_detection(policy):
    """Demonstrate fraud detection capabilities."""
    
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Fraud Detection")
    print("=" * 70)
    
    # High-value item purchased and returned immediately
    suspicious_product = Product(
        product_id="prod_expensive",
        name="Premium Gaming Setup (Monitor + PC)",
        category="electronics",
        price=3499.99,  # Very high value
        purchase_date=datetime.now() - timedelta(hours=2),  # Purchased 2 hours ago!
        condition="unopened",
        seller_id="seller_electronics_001",
        seller_name="TechStore Electronics",
        sku="TECH-SETUP-PREMIUM"
    )
    
    suspicious_return = ReturnRequest(
        return_id="ret_fraud_001",
        customer_id="cust_789",
        product=suspicious_product,
        reason=ReturnReason.CHANGED_MIND,
        description="Found a better deal",
        reason_category="preference"
    )
    
    print(f"\n🚩 Flagged Return:")
    print(f"  Product: {suspicious_product.name}")
    print(f"  Price: ${suspicious_product.price:.2f}")
    print(f"  Purchased: {suspicious_product.purchase_date.strftime('%H:%M')}")
    print(f"  Time Since Purchase: ~2 hours")
    print(f"  Reason: {suspicious_return.reason.value}")
    
    engine = EligibilityEngine(policy)
    fraud_score, fraud_msg = engine._check_fraud_patterns(suspicious_return)
    
    print(f"\n⚠️ Fraud Score: {fraud_score:.1%}")
    print(f"Risk Indicators:")
    indicators = fraud_msg.split(" | ")
    for indicator in indicators:
        print(f"  • {indicator}")
    
    if fraud_score > 0.7:
        print(f"\n🚨 ALERT: This return should be flagged for manual review!")


# ============================================================================
# Main Demo
# ============================================================================

def main():
    """Run all examples."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " E-Commerce Returns Assistant - Demo & Examples".center(68) + "║")
    print("╚" + "=" * 68 + "╝")
    
    # Run examples in sequence
    policy = example_policy_compression()
    return_request = example_eligibility_checking(policy)
    example_conversation_handling(policy, return_request)
    example_ineligible_return(policy)
    example_fraud_detection(policy)
    
    print("\n" + "=" * 70)
    print("Demo Complete! ✅")
    print("=" * 70)
    print("\nKey Takeaways:")
    print("✓ Policies are automatically compressed into actionable rules")
    print("✓ Eligibility checks are transparent with detailed reasoning")
    print("✓ Conversations are natural and context-aware")
    print("✓ Fraud detection flags suspicious patterns")
    print("✓ System provides clear next steps to customers\n")


if __name__ == "__main__":
    main()
