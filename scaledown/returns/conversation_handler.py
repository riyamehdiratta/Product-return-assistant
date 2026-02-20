"""
Conversation Handler: Manages natural language conversations for returns.

Features:
- Natural language queries about eligibility, refunds, replacements
- Sentiment detection and escalation
- Multi-turn conversations with context
- Chat + WhatsApp-style responses
"""

from typing import Optional, List, Dict, Tuple
from datetime import datetime
import re

from .types import (
    ConversationContext,
    ReturnPolicy,
    Product,
    ReturnRequest,
    ReturnReason
)
from .eligibility_engine import EligibilityEngine


class ConversationHandler:
    """
    Handles natural language conversations for return-related queries.
    
    Capabilities:
    - Answer questions about return policies
    - Check return eligibility
    - Process return requests
    - Detect sentiment and escalate if needed
    - Provide step-by-step guidance
    """
    
    def __init__(self, policies: Dict[str, ReturnPolicy], 
                 escalation_threshold: float = 0.7):
        """
        Initialize conversation handler.
        
        Parameters
        ----------
        policies : Dict[str, ReturnPolicy]
            Mapping of seller_id -> ReturnPolicy
        escalation_threshold : float
            Frustration level at which to escalate to human (0-1)
        """
        self.policies = policies
        self.escalation_threshold = escalation_threshold
        self.intent_patterns = self._build_intent_patterns()
    
    def handle_message(self, context: ConversationContext, 
                       user_message: str) -> Tuple[str, ConversationContext]:
        """
        Handle a user message in a conversation.
        
        Parameters
        ----------
        context : ConversationContext
            Current conversation context
        user_message : str
            User's message
        
        Returns
        -------
        Tuple[str, ConversationContext]
            Assistant response and updated context
        """
        # Update conversation history
        context.messages.append({"role": "user", "content": user_message})
        context.message_count += 1
        context.updated_at = datetime.now()
        
        # Detect sentiment
        sentiment, frustration_level = self._detect_sentiment(user_message)
        context.customer_sentiment = sentiment
        context.frustration_level = frustration_level
        
        # Check if escalation needed
        if frustration_level > self.escalation_threshold:
            context.escalation_required = True
            context.escalation_reason = f"High frustration detected ({frustration_level:.1%})"
            response = self._escalate_to_human(context)
            context.messages.append({"role": "assistant", "content": response})
            return response, context
        
        # Detect intent
        intent, extracted_data = self._extract_intent(user_message, context)
        
        # Route to appropriate handler
        if intent == "check_eligibility":
            response = self._handle_eligibility_check(context, extracted_data)
        elif intent == "policy_question":
            response = self._handle_policy_question(context, extracted_data)
        elif intent == "initiate_return":
            response = self._handle_initiate_return(context, extracted_data)
        elif intent == "refund_status":
            response = self._handle_refund_status(context, extracted_data)
        elif intent == "replacement_request":
            response = self._handle_replacement_request(context, extracted_data)
        elif intent == "pickup_scheduling":
            response = self._handle_pickup_scheduling(context, extracted_data)
        elif intent == "track_return":
            response = self._handle_track_return(context, extracted_data)
        else:
            response = self._handle_general_query(context, user_message)
        
        # Add to conversation history
        context.messages.append({"role": "assistant", "content": response})
        
        return response, context
    
    def _detect_sentiment(self, message: str) -> Tuple[str, float]:
        """
        Detect sentiment and frustration level from message.
        
        Returns
        -------
        Tuple[str, float]
            Sentiment ("satisfied", "neutral", "frustrated", "angry") 
            and frustration level (0-1)
        """
        message_lower = message.lower()
        
        # Angry indicators
        angry_words = ["angry", "outrageous", "terrible", "worst", "scam", "fraud", "criminal"]
        if any(word in message_lower for word in angry_words):
            return "angry", 0.9
        
        # Frustrated indicators
        frustrated_words = ["frustrated", "disappointed", "upset", "annoyed", "fed up", "ridiculous"]
        if any(word in message_lower for word in frustrated_words):
            return "frustrated", 0.7
        
        # Satisfied indicators
        satisfied_words = ["thank", "appreciate", "grateful", "love", "perfect", "great", "excellent"]
        if any(word in message_lower for word in satisfied_words):
            return "satisfied", 0.1
        
        # Neutral is default
        return "neutral", 0.3
    
    def _extract_intent(self, message: str, 
                       context: ConversationContext) -> Tuple[str, dict]:
        """
        Extract user intent from message.
        
        Returns
        -------
        Tuple[str, dict]
            Intent type and extracted data
        """
        message_lower = message.lower()
        
        # Check each intent pattern
        for intent, patterns in self.intent_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    data = self._extract_entities(message, intent, context)
                    return intent, data
        
        # Default to general query
        return "general_query", {}
    
    def _extract_entities(self, message: str, intent: str, 
                         context: ConversationContext) -> dict:
        """Extract relevant entities from message based on intent."""
        entities = {}
        
        if intent == "check_eligibility" and context.current_return_request:
            # Already have return request in context
            entities["return_request"] = context.current_return_request
        elif intent == "initiate_return":
            # Extract product info from message
            entities["product_name"] = self._extract_product_name(message)
            entities["reason"] = self._extract_return_reason(message)
        elif intent == "pickup_scheduling":
            # Extract date/time preferences
            entities["preferred_date"] = self._extract_date(message)
            entities["time_window"] = self._extract_time_window(message)
        
        return entities
    
    def _handle_eligibility_check(self, context: ConversationContext, 
                                  data: dict) -> str:
        """Handle eligibility check requests."""
        if not context.current_return_request or not context.policy_context:
            return "I need more information about your return. Could you tell me:\n1. Which product are you returning?\n2. What's the reason for the return?\n3. When did you purchase it?"
        
        # Run eligibility check
        engine = EligibilityEngine(context.policy_context)
        result = engine.check_eligibility(context.current_return_request)
        
        # Build response
        if result.is_eligible:
            response = "✅ Great news! Your return is eligible.\n\n"
            response += "**Why this return is accepted:**\n"
            for reason in result.checks_passed:
                response += f"• {reason}\n"
            
            if result.suggestions:
                response += "\n**What's next:**\n"
                response += "1. We'll email you a return shipping label\n"
                response += "2. Pack your item securely\n"
                response += "3. Drop off at a carrier location\n"
                response += "4. You'll get your refund within 5-7 business days\n"
                response += "\n**Your options:**\n"
                for suggestion in result.suggestions:
                    response += f"• {suggestion}\n"
        else:
            response = "❌ Unfortunately, this return doesn't meet our policy requirements.\n\n"
            response += "**Reasons:**\n"
            for reason in result.reasons:
                response += f"• {reason}\n"
            
            if result.warnings:
                response += "\n**⚠️ Note:**\n"
                for warning in result.warnings:
                    response += f"• {warning}\n"
            
            if result.suggestions:
                response += "\n**Alternative options:**\n"
                for suggestion in result.suggestions:
                    response += f"• {suggestion}\n"
        
        return response
    
    def _handle_policy_question(self, context: ConversationContext, 
                               data: dict) -> str:
        """Handle general policy questions."""
        if not context.policy_context:
            return "I don't have your seller's policy information. Could you tell me which seller this is for?"
        
        policy = context.policy_context
        
        # Build policy summary
        response = "📋 **Our Return Policy:**\n\n"
        response += f"**Return Window:** {policy.return_window_days} days from purchase\n"
        response += f"**Refund Type:** {policy.refund_type.upper()}\n"
        
        if policy.refund_deduction_pct > 0:
            response += f"**Restocking Fee:** {policy.refund_deduction_pct}%\n"
        
        response += f"**Eligible Conditions:** {', '.join(policy.eligible_categories)}\n"
        
        if policy.exclusions:
            response += f"**Cannot Return:** {', '.join(policy.exclusions)}\n"
        
        response += f"**Refund Processing:** {policy.refund_time_days} business days\n"
        
        if policy.supports_replacement:
            response += "**Supports:** ✅ Replacements\n"
        
        if policy.supports_pickup:
            response += "**Supports:** ✅ Free pickup\n"
        
        return response
    
    def _handle_initiate_return(self, context: ConversationContext, 
                               data: dict) -> str:
        """Handle return initiation requests."""
        product_name = data.get("product_name", "your item")
        reason = data.get("reason", "to be determined")
        
        response = f"Got it! You'd like to return {product_name} because {reason}.\n\n"
        response += "To complete your return request, I need a bit more info:\n"
        response += "1. What's the product's current condition? (new, unopened, gently used, damaged)\n"
        response += "2. When did you purchase it?\n"
        response += "3. What's your order number? (optional)\n\n"
        response += "Once I have these details, I can check if your return is eligible! ✨"
        
        return response
    
    def _handle_refund_status(self, context: ConversationContext, 
                             data: dict) -> str:
        """Handle refund status queries."""
        if not context.current_return_request:
            return "I don't have an active return request for you. Would you like to initiate a new return?"
        
        return_request = context.current_return_request
        response = f"📊 **Return Status for {return_request.product.name}**\n\n"
        response += f"**Current Status:** {return_request.status.value.upper()}\n"
        response += f"**Refund Status:** {return_request.refund_status.value.upper()}\n"
        
        if return_request.refund_amount > 0:
            response += f"**Refund Amount:** ${return_request.refund_amount:.2f}\n"
        
        if return_request.received_at:
            response += f"**Received Date:** {return_request.received_at.strftime('%Y-%m-%d')}\n"
        
        response += "\nExpected refund processing: 5-7 business days from receipt\n"
        
        return response
    
    def _handle_replacement_request(self, context: ConversationContext, 
                                   data: dict) -> str:
        """Handle replacement requests."""
        if not context.policy_context or not context.policy_context.supports_replacement:
            return "Unfortunately, replacements are not available for this seller's products."
        
        response = "✨ **Replacement Request**\n\n"
        response += "Great! We can send you a replacement.\n\n"
        response += "What would you like?\n"
        response += "1. Same product (different unit)\n"
        response += "2. Different size/color/variant\n"
        response += "3. Different product at similar price point\n\n"
        response += "Let me know your preference and I'll get it set up! 📦"
        
        return response
    
    def _handle_pickup_scheduling(self, context: ConversationContext, 
                                 data: dict) -> str:
        """Handle pickup scheduling requests."""
        if not context.policy_context or not context.policy_context.supports_pickup:
            return "Pickup service is not available for this seller. You'll need to ship your return."
        
        response = "🚗 **Free Return Pickup**\n\n"
        response += "Excellent! We can arrange free pickup for you.\n\n"
        response += "When would you like us to pick up?\n"
        response += "• Today (between 2-6 PM)\n"
        response += "• Tomorrow (morning or afternoon)\n"
        response += "• Specific date/time? (just let me know)\n\n"
        response += "Also, what's the best address for pickup?"
        
        return response
    
    def _handle_track_return(self, context: ConversationContext, 
                            data: dict) -> str:
        """Handle return tracking requests."""
        if not context.current_return_request:
            return "I don't have a return to track. Do you have a return ID or order number?"
        
        return_request = context.current_return_request
        response = f"📍 **Tracking Return {return_request.return_id}**\n\n"
        
        if return_request.return_label_url:
            response += f"**Shipping Label:** [Download Label]({return_request.return_label_url})\n\n"
        
        response += f"**Timeline:**\n"
        response += f"✅ Return created: {return_request.created_at.strftime('%Y-%m-%d')}\n"
        
        if return_request.received_at:
            response += f"✅ Received: {return_request.received_at.strftime('%Y-%m-%d')}\n"
        else:
            response += f"⏳ In transit...\n"
        
        if return_request.refunded_at:
            response += f"✅ Refunded: {return_request.refunded_at.strftime('%Y-%m-%d')}\n"
        else:
            response += f"⏳ Processing refund...\n"
        
        return response
    
    def _handle_general_query(self, context: ConversationContext, 
                             message: str) -> str:
        """Handle general queries not matching specific intents."""
        # Simple keyword matching for common questions
        if "how long" in message.lower():
            return "Our typical refund processing takes 5-7 business days after we receive your return. The return shipping itself may take 3-5 days."
        elif "condition" in message.lower():
            return "Your item should ideally be in its original condition. Minor wear is usually acceptable, but items should not be damaged."
        elif "shipping" in message.lower():
            return "We'll provide you with a prepaid return shipping label. Most carriers offer free pickup options!"
        elif "contact" in message.lower() or "support" in message.lower():
            return "Our support team is available:\n📧 Email: support@example.com\n📞 Phone: 1-800-RETURNS (1-800-738-8767)\n💬 Live chat: Available Mon-Fri, 9 AM - 6 PM"
        
        # Default response
        return "I'm here to help with returns! You can ask me about:\n• Return eligibility\n• Our return policy\n• How to start a return\n• Refund status\n• Replacement options\n• Pickup scheduling\n\nWhat would you like to know?"
    
    def _escalate_to_human(self, context: ConversationContext) -> str:
        """Generate escalation message for human support."""
        return f"I notice you might be frustrated, and I want to make sure you get the best help. 🙏\n\nI'm connecting you with our human support team who can provide personalized assistance.\n\n**Support Team Contact:**\n📧 Email: support@example.com\n📞 Phone: 1-800-RETURNS\n💬 Chat: A specialist will be with you shortly\n\nWe appreciate your patience and will resolve this as quickly as possible!"
    
    def _build_intent_patterns(self) -> Dict[str, List[str]]:
        """Build regex patterns for intent detection."""
        return {
            "check_eligibility": [
                r"eligible|can i return|able to return|can i send back",
                r"will you accept|do you accept|acceptable condition",
            ],
            "policy_question": [
                r"policy|policies|return window|how long|how many days",
                r"refund|restocking fee|deduction",
            ],
            "initiate_return": [
                r"i want to return|i'd like to return|start a return|initiate return",
                r"return this|send back|get my money back",
            ],
            "refund_status": [
                r"refund status|where is my refund|when will i get|check status",
                r"payment|money back|received",
            ],
            "replacement_request": [
                r"replacement|different one|exchange|swap|different size|different color",
            ],
            "pickup_scheduling": [
                r"pickup|pick up|come get|collect|arrange pickup|schedule pickup",
            ],
            "track_return": [
                r"track|tracking|where is|status|arrived|received",
            ],
        }
    
    def _extract_product_name(self, message: str) -> str:
        """Extract product name from message."""
        # Simple extraction: look for quoted text or product-like phrases
        quoted = re.findall(r'"([^"]*)"', message)
        if quoted:
            return quoted[0]
        return "your item"
    
    def _extract_return_reason(self, message: str) -> str:
        """Extract return reason from message."""
        message_lower = message.lower()
        
        reason_map = {
            "defective|broken|stopped working|not working": ReturnReason.DEFECTIVE,
            "damaged|arrived damaged|broken": ReturnReason.DAMAGED,
            "not as described|different|doesn't match": ReturnReason.NOT_AS_DESCRIBED,
            "wrong item|wrong product|wrong size|shipped wrong": ReturnReason.WRONG_ITEM,
            "changed my mind|don't want|don't need": ReturnReason.CHANGED_MIND,
        }
        
        for pattern, reason in reason_map.items():
            if re.search(pattern, message_lower):
                return reason.value
        
        return "not specified"
    
    def _extract_date(self, message: str) -> Optional[str]:
        """Extract preferred date from message."""
        # Simple date extraction
        date_patterns = {
            "today": "today",
            "tomorrow": "tomorrow",
            r"(\d{1,2})[/-](\d{1,2})": "custom_date",
        }
        
        for pattern in date_patterns:
            if re.search(pattern, message.lower()):
                return date_patterns[pattern]
        
        return None
    
    def _extract_time_window(self, message: str) -> str:
        """Extract time window preference from message."""
        if "morning" in message.lower():
            return "morning"
        elif "afternoon" in message.lower() or "evening" in message.lower():
            return "afternoon"
        elif re.search(r"(\d{1,2})\s*(?:am|pm|a\.m|p\.m)", message):
            return "specific_time"
        else:
            return "flexible"
