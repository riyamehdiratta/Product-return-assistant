"""
Eligibility Engine: Determines if a return meets policy requirements.

Performs step-by-step eligibility checks with explainable decisions.
Checks: return window, product condition, category, exclusions, etc.
"""

from typing import Optional, List, Tuple
from datetime import datetime, timedelta

from .types import (
    ReturnPolicy, 
    Product, 
    ReturnRequest, 
    ReturnReason,
    EligibilityResult
)


class EligibilityEngine:
    """
    Checks return eligibility against a policy with explainable reasoning.
    
    Performs checks:
    - Return window: Is the return within the allowed timeframe?
    - Product condition: Does the product condition match policy requirements?
    - Category eligibility: Is the product category eligible for return?
    - Exclusions: Is the product on the exclusion list?
    - Special cases: Damaged items, defective items, etc.
    """
    
    def __init__(self, policy: ReturnPolicy):
        """
        Initialize eligibility engine with a policy.
        
        Parameters
        ----------
        policy : ReturnPolicy
            The return policy to check against
        """
        self.policy = policy
    
    def check_eligibility(self, return_request: ReturnRequest) -> EligibilityResult:
        """
        Check if a return request is eligible.
        
        Performs comprehensive eligibility checks with detailed reasoning.
        
        Parameters
        ----------
        return_request : ReturnRequest
            The return request to check
        
        Returns
        -------
        EligibilityResult
            Detailed eligibility result with reasons and explanations
        """
        checks_passed = []
        checks_failed = []
        reasons = []
        warnings = []
        suggestions = []
        
        # 1. Check return window
        is_within_window, window_msg = self._check_return_window(return_request)
        if is_within_window:
            checks_passed.append("Return within policy window")
        else:
            checks_failed.append("Return outside policy window")
            reasons.append(window_msg)
        
        # 2. Check product category
        is_category_eligible, cat_msg = self._check_category_eligibility(return_request)
        if is_category_eligible:
            checks_passed.append("Product category is eligible")
        else:
            checks_failed.append("Product category not eligible")
            reasons.append(cat_msg)
        
        # 3. Check product condition
        is_condition_eligible, cond_msg = self._check_condition_eligibility(return_request)
        if is_condition_eligible:
            checks_passed.append("Product condition meets requirements")
        else:
            if return_request.reason in [ReturnReason.DEFECTIVE, ReturnReason.DAMAGED]:
                # Damaged/defective items may have special handling
                warnings.append(cond_msg)
                checks_passed.append("Defective/damaged items covered")
            else:
                checks_failed.append("Product condition doesn't meet requirements")
                reasons.append(cond_msg)
        
        # 4. Check exclusions
        is_not_excluded, excl_msg = self._check_exclusions(return_request)
        if is_not_excluded:
            checks_passed.append("Product is not on exclusion list")
        else:
            checks_failed.append("Product is on exclusion list")
            reasons.append(excl_msg)
            suggestions.append("This item is final sale. No returns are accepted.")
        
        # 5. Check for fraud patterns
        fraud_score, fraud_msg = self._check_fraud_patterns(return_request)
        if fraud_score < 0.5:
            checks_passed.append("Fraud check passed")
        else:
            warnings.append(fraud_msg)
            if fraud_score > 0.7:
                checks_failed.append("High fraud risk detected")
                reasons.append("This return has been flagged for review")
        
        # 6. Determine overall eligibility
        is_eligible = len(checks_failed) == 0
        
        # Add general suggestions for approved returns
        if is_eligible:
            if self.policy.supports_replacement:
                suggestions.append("You can choose a replacement instead of refund if preferred")
            if self.policy.supports_pickup:
                suggestions.append("Free pickup available if you prefer not to ship")
        
        return EligibilityResult(
            is_eligible=is_eligible,
            reasons=reasons,
            warnings=warnings,
            suggestions=suggestions,
            checks_passed=checks_passed,
            checks_failed=checks_failed
        )
    
    def _check_return_window(self, return_request: ReturnRequest) -> Tuple[bool, str]:
        """Check if return is within the policy window."""
        days_since_purchase = (datetime.now() - return_request.product.purchase_date).days
        
        if days_since_purchase <= self.policy.return_window_days:
            return True, f"Return submitted {days_since_purchase} days after purchase (within {self.policy.return_window_days}-day window)"
        else:
            return False, f"Return submitted {days_since_purchase} days after purchase (exceeds {self.policy.return_window_days}-day window)"
    
    def _check_category_eligibility(self, return_request: ReturnRequest) -> Tuple[bool, str]:
        """Check if product category is eligible."""
        if "all" in self.policy.eligible_categories:
            return True, "All categories are eligible"
        
        if return_request.product.category in self.policy.eligible_categories:
            return True, f"Category '{return_request.product.category}' is eligible"
        else:
            eligible = ", ".join(self.policy.eligible_categories)
            return False, f"Category '{return_request.product.category}' is not in eligible list: {eligible}"
    
    def _check_condition_eligibility(self, return_request: ReturnRequest) -> Tuple[bool, str]:
        """Check if product condition meets requirements."""
        if "all" in self.policy.eligible_conditions or "*" in self.policy.eligible_conditions:
            return True, "All conditions are acceptable"
        
        if return_request.product.condition in self.policy.eligible_conditions:
            return True, f"Condition '{return_request.product.condition}' is acceptable"
        else:
            conditions = ", ".join(self.policy.eligible_conditions)
            return False, f"Condition '{return_request.product.condition}' doesn't match acceptable conditions: {conditions}"
    
    def _check_exclusions(self, return_request: ReturnRequest) -> Tuple[bool, str]:
        """Check if product is on exclusion list."""
        product_name = return_request.product.name.lower()
        
        for exclusion in self.policy.exclusions:
            if exclusion.lower() in product_name:
                return False, f"Product matches exclusion pattern: {exclusion}"
        
        # Check final sale items
        for final_sale in self.policy.final_sale_items:
            if final_sale.lower() in product_name or final_sale.lower() in return_request.product.category.lower():
                return False, f"Product is in final sale category: {final_sale}"
        
        return True, "Product is not on exclusion list"
    
    def _check_fraud_patterns(self, return_request: ReturnRequest) -> Tuple[float, str]:
        """
        Detect potential fraud or abuse patterns.
        
        Returns
        -------
        Tuple[float, str]
            Fraud score (0-1) and explanation
        """
        fraud_score = 0.0
        fraud_reasons = []
        
        # Check for suspiciously high-value returns
        if return_request.product.price > 500:
            fraud_score += 0.1
            fraud_reasons.append(f"High-value item (${return_request.product.price})")
        
        # Check for returns immediately after purchase
        days_since_purchase = (datetime.now() - return_request.product.purchase_date).days
        if days_since_purchase <= 1:
            fraud_score += 0.15
            fraud_reasons.append("Return submitted very quickly after purchase")
        
        # Check reason
        high_risk_reasons = [ReturnReason.CHANGED_MIND, ReturnReason.OTHER]
        if return_request.reason in high_risk_reasons:
            fraud_score += 0.05
            fraud_reasons.append(f"Reason '{return_request.reason.value}' is common for returns abuse")
        
        msg = " | ".join(fraud_reasons) if fraud_reasons else "No fraud indicators detected"
        return fraud_score, msg
    
    def calculate_refund_amount(self, return_request: ReturnRequest) -> Tuple[float, str]:
        """
        Calculate the refund amount based on policy rules.
        
        Parameters
        ----------
        return_request : ReturnRequest
            The return request
        
        Returns
        -------
        Tuple[float, str]
            Refund amount and explanation
        """
        original_price = return_request.product.price
        deduction_reason = ""
        
        # Apply deductions if needed
        if self.policy.refund_deduction_pct > 0:
            deduction = original_price * (self.policy.refund_deduction_pct / 100)
            refund_amount = original_price - deduction
            deduction_reason = f"Restocking fee of {self.policy.refund_deduction_pct}% applied"
        else:
            refund_amount = original_price
            deduction_reason = "Full refund (no deductions)"
        
        # Check for special cases
        if return_request.reason == ReturnReason.DEFECTIVE:
            refund_amount = original_price  # Full refund for defects
            deduction_reason = "Full refund for defective item"
        elif return_request.reason == ReturnReason.WRONG_ITEM:
            refund_amount = original_price  # Full refund for wrong items
            deduction_reason = "Full refund for wrong item shipped"
        elif return_request.product.condition == "damaged":
            # Adjust refund based on damage
            refund_amount = original_price * 0.7  # 30% deduction for damage
            deduction_reason = "30% deduction applied for item damage"
        
        return refund_amount, deduction_reason
    
    def get_next_steps(self, eligibility_result: EligibilityResult) -> List[str]:
        """
        Get next steps for the customer based on eligibility result.
        
        Parameters
        ----------
        eligibility_result : EligibilityResult
            The eligibility check result
        
        Returns
        -------
        List[str]
            Ordered list of next steps
        """
        steps = []
        
        if eligibility_result.is_eligible:
            steps.append("1. Return approved! 📦")
            steps.append("2. A return shipping label will be sent to your email")
            steps.append("3. Package your item securely with original packaging (if required)")
            steps.append("4. Drop off at your nearest carrier location")
            steps.append("5. We'll inspect and process your refund within 5-7 business days")
        else:
            steps.append("Unfortunately, this return doesn't meet our policy requirements.")
            if eligibility_result.suggestions:
                steps.append("\nBut we can help! Here are some alternatives:")
                steps.extend(eligibility_result.suggestions)
            steps.append("\nNeed help? Contact our support team at support@example.com")
        
        return steps
