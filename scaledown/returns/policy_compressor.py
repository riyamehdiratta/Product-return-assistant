"""
Policy Compressor: Compresses long return policies into clear, actionable rules.

Uses the ScaleDown compression framework to reduce policy text while preserving 
critical information like return windows, eligibility rules, exclusions, and timelines.
"""

from typing import Optional, List
from datetime import datetime
import re
import json

from scaledown.compressor.base import BaseCompressor
from scaledown.types import CompressedPrompt
from .types import ReturnPolicy


class PolicyCompressor(BaseCompressor):
    """
    Compresses return policies (PDF/web/text) into structured, actionable rules.
    
    Extracts key information:
    - Return window (days)
    - Refund type (full/partial/store credit)
    - Eligible categories
    - Exclusions
    - Refund deduction percentages
    - Timeline for approval and refunds
    """
    
    def __init__(self, rate: float = "auto", api_key: Optional[str] = None, 
                 extraction_prompt: Optional[str] = None):
        """
        Initialize PolicyCompressor.
        
        Parameters
        ----------
        rate : float or 'auto'
            Compression rate for the policy text
        api_key : str, optional
            API key for compression service
        extraction_prompt : str, optional
            Custom prompt for policy extraction
        """
        super().__init__(rate=rate, api_key=api_key)
        self.extraction_prompt = extraction_prompt or self._default_extraction_prompt()
    
    def _default_extraction_prompt(self) -> str:
        """Default prompt for extracting policy information."""
        return """Extract the following information from the return policy:
1. Return window (in days)
2. Refund type (full, partial, store credit, or mixed)
3. Refund deduction percentage (if any)
4. Eligible product categories
5. Eligible product conditions (new, unopened, gently_used, etc.)
6. Non-returnable items/exclusions
7. Final sale categories
8. Approval time (in hours)
9. Refund processing time (in days)
10. Supports replacement option (yes/no)
11. Supports pickup (yes/no)
12. Original packaging requirement (yes/no)

Format the output as JSON with these exact keys:
{
    "return_window_days": int,
    "refund_type": str,
    "refund_deduction_pct": float,
    "eligible_categories": [str],
    "eligible_conditions": [str],
    "exclusions": [str],
    "final_sale_items": [str],
    "approval_time_hours": int,
    "refund_time_days": int,
    "supports_replacement": bool,
    "supports_pickup": bool,
    "requires_original_packaging": bool
}"""
    
    def compress(self, policy_text: str, prompt: Optional[str] = None, 
                 max_tokens: Optional[int] = None) -> CompressedPrompt:
        """
        Compress a return policy into structured rules.
        
        Parameters
        ----------
        policy_text : str
            Raw return policy text (from PDF, web, or document)
        prompt : str, optional
            Additional context or specific extraction requirements
        max_tokens : int, optional
            Maximum tokens for compressed output
        
        Returns
        -------
        CompressedPrompt
            Compressed policy with metrics
        """
        # Combine extraction prompt with any additional instructions
        full_prompt = self.extraction_prompt
        if prompt:
            full_prompt += f"\n\nAdditional instructions: {prompt}"
        
        # Call parent's compress method (uses ScaleDown API)
        # This would call the API in production
        compressed = super().compress(
            context=policy_text,
            prompt=full_prompt,
            max_tokens=max_tokens or 1000
        )
        
        return compressed
    
    def parse_policy(self, policy_text: str, seller_id: str, 
                     policy_name: str) -> ReturnPolicy:
        """
        Parse and compress a policy, returning a structured ReturnPolicy object.
        
        Parameters
        ----------
        policy_text : str
            Raw policy text
        seller_id : str
            ID of the seller
        policy_name : str
            Name of the policy
        
        Returns
        -------
        ReturnPolicy
            Structured policy with extracted rules
        """
        # Compress the policy
        compressed = self.compress(policy_text)
        
        # Try to parse as JSON (from API or local extraction)
        policy_dict = self._extract_policy_dict(policy_text)
        
        # Create ReturnPolicy object
        policy = ReturnPolicy(
            policy_id=self._generate_policy_id(),
            seller_id=seller_id,
            policy_name=policy_name,
            return_window_days=policy_dict.get("return_window_days", 30),
            refund_type=policy_dict.get("refund_type", "full"),
            refund_deduction_pct=policy_dict.get("refund_deduction_pct", 0.0),
            eligible_categories=policy_dict.get("eligible_categories", ["all"]),
            eligible_conditions=policy_dict.get("eligible_conditions", ["new"]),
            exclusions=policy_dict.get("exclusions", []),
            final_sale_items=policy_dict.get("final_sale_items", []),
            approval_time_hours=policy_dict.get("approval_time_hours", 24),
            refund_time_days=policy_dict.get("refund_time_days", 5),
            supports_replacement=policy_dict.get("supports_replacement", True),
            supports_pickup=policy_dict.get("supports_pickup", False),
            requires_original_packaging=policy_dict.get("requires_original_packaging", False),
            original_policy_text=policy_text,
            original_policy_tokens=self._count_tokens(policy_text),
            compressed_policy_tokens=self._count_tokens(str(compressed))
        )
        
        return policy
    
    def _extract_policy_dict(self, policy_text: str) -> dict:
        """
        Extract policy information from text using pattern matching and heuristics.
        
        This is a fallback extraction method when API is not available.
        """
        extracted = {
            "return_window_days": self._extract_return_window(policy_text),
            "refund_type": self._extract_refund_type(policy_text),
            "refund_deduction_pct": self._extract_deduction_pct(policy_text),
            "eligible_categories": self._extract_categories(policy_text),
            "eligible_conditions": self._extract_conditions(policy_text),
            "exclusions": self._extract_exclusions(policy_text),
            "final_sale_items": self._extract_final_sale(policy_text),
            "approval_time_hours": self._extract_approval_time(policy_text),
            "refund_time_days": self._extract_refund_time(policy_text),
            "supports_replacement": self._extract_supports_replacement(policy_text),
            "supports_pickup": self._extract_supports_pickup(policy_text),
            "requires_original_packaging": self._extract_packaging_requirement(policy_text),
        }
        return extracted
    
    def _extract_return_window(self, text: str) -> int:
        """Extract return window in days."""
        patterns = [
            r"(\d+)\s*(?:day|days)\s*(?:to\s*)?return",
            r"return\s*(?:within|for|in)\s*(\d+)\s*(?:day|days)",
            r"(?:window|period).*?(\d+)\s*(?:day|days)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        return 30  # Default
    
    def _extract_refund_type(self, text: str) -> str:
        """Extract refund type."""
        if "full refund" in text.lower():
            return "full"
        elif "partial" in text.lower():
            return "partial"
        elif "store credit" in text.lower():
            return "store_credit"
        elif "replacement only" in text.lower():
            return "replacement"
        return "full"
    
    def _extract_deduction_pct(self, text: str) -> float:
        """Extract refund deduction percentage."""
        pattern = r"(\d+(?:\.\d+)?)\s*%\s*(?:deduction|restocking|handling)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return 0.0
    
    def _extract_categories(self, text: str) -> List[str]:
        """Extract eligible categories."""
        # Simple heuristic: look for common category mentions
        categories = []
        common_categories = [
            "electronics", "clothing", "shoes", "books", "furniture",
            "home goods", "sports", "toys", "beauty", "health"
        ]
        for cat in common_categories:
            if cat.lower() in text.lower():
                categories.append(cat)
        
        return categories or ["all"]
    
    def _extract_conditions(self, text: str) -> List[str]:
        """Extract eligible conditions."""
        conditions = []
        condition_map = {
            "new": ["new", "unopened"],
            "unopened": ["unopened", "sealed"],
            "gently_used": ["gently used", "lightly used", "worn"],
            "used": ["used", "worn"],
        }
        
        for condition, keywords in condition_map.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    conditions.append(condition)
                    break
        
        return conditions or ["new"]
    
    def _extract_exclusions(self, text: str) -> List[str]:
        """Extract non-returnable items."""
        exclusions = []
        exclusion_patterns = [
            r"(?:non-?returnable|not\s+eligible|cannot\s+return|excluded|exclusions?).*?:?\s*([^.]+)",
            r"(?:EXCLUSIONS|Non-?returnable|Cannot return).*?(?:items?|products?)[\s:]*([^.]+)",
        ]
        
        for pattern in exclusion_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                # Split by commas if multiple items listed
                items = [item.strip() for item in m.split(",") if item.strip()]
                exclusions.extend(items)
        
        # Remove duplicates and empty strings
        exclusions = list(set([e for e in exclusions if e.strip()]))
        
        return exclusions
    
    def _extract_final_sale(self, text: str) -> List[str]:
        """Extract final sale items."""
        # Look for final sale mentions
        if "final sale" in text.lower():
            return ["clearance", "final sale items"]
        return []
    
    def _extract_approval_time(self, text: str) -> int:
        """Extract approval time in hours."""
        pattern = r"(?:approv|review).*?(\d+)\s*(?:hour|hours|business\s+day)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hours = int(match.group(1))
            if "day" in match.group(0).lower():
                hours = hours * 24  # Convert days to hours
            return hours
        return 24  # Default
    
    def _extract_refund_time(self, text: str) -> int:
        """Extract refund processing time in days."""
        pattern = r"(?:refund|process).*?(\d+)\s*(?:business\s+)?(?:day|days)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 5  # Default
    
    def _extract_supports_replacement(self, text: str) -> bool:
        """Check if policy supports replacement."""
        return "replacement" in text.lower() and "no replacement" not in text.lower()
    
    def _extract_supports_pickup(self, text: str) -> bool:
        """Check if policy supports pickup."""
        return "pickup" in text.lower() and "no pickup" not in text.lower()
    
    def _extract_packaging_requirement(self, text: str) -> bool:
        """Check if original packaging is required."""
        return "original packaging" in text.lower() or "original box" in text.lower()
    
    def _generate_policy_id(self) -> str:
        """Generate a unique policy ID."""
        import uuid
        return f"policy_{uuid.uuid4().hex[:12]}"
    
    def _count_tokens(self, text: str) -> int:
        """Approximate token count (simple word-based estimation)."""
        # Simple heuristic: ~1.3 tokens per word
        words = len(text.split())
        return int(words * 1.3)
