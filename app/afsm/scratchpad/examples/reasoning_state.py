"""
Example of using the scratchpad module with the AFSM architecture.
"""

from typing import Any, Dict, List, Optional, Tuple

from app.afsm.scratchpad.integration import ScratchpadStateMixin
from app.afsm.scratchpad.section import SectionType
from app.states import AFSMState, StateContext, StateTransition


class ReasoningState(AFSMState, ScratchpadStateMixin):
    """
    Base class for states that perform reasoning using the scratchpad.

    This combines the AFSMState with the ScratchpadStateMixin to create
    a state that can track its reasoning process.
    """

    def __init__(
        self,
        name: str,
        description: str,
        allowed_transitions: Optional[List[StateTransition]] = None,
    ):
        """
        Initialize the reasoning state.

        Args:
            name: Name of the state
            description: Description of the state
            allowed_transitions: List of allowed transitions
        """
        AFSMState.__init__(
            self,
            name=name,
            description=description,
            allowed_transitions=allowed_transitions or [],
        )
        ScratchpadStateMixin.__init__(self)

    async def process(
        self, input_text: str, context: StateContext
    ) -> Tuple[str, Optional[str], StateContext]:
        """
        Process input and produce a response using structured reasoning.

        Args:
            input_text: Input text from the user
            context: Current state context

        Returns:
            Tuple of (response, next_state_name, updated_context)
        """
        # Record the input
        self.write_to_scratchpad(f"USER INPUT: {input_text}")

        # Start reasoning process
        self.write_to_scratchpad("Beginning reasoning process...")

        # Extract facts from input
        facts = self._extract_facts(input_text, context)
        for fact in facts:
            self.write_fact(fact)

        # Form hypotheses
        hypotheses = self._form_hypotheses(facts, context)
        for hypothesis in hypotheses:
            self.write_to_state_section(self.name, SectionType.HYPOTHESES, hypothesis)

        # Draw conclusions
        conclusions = self._draw_conclusions(facts, hypotheses, context)
        for conclusion in conclusions:
            self.write_conclusion(conclusion)

        # Determine next state
        next_state = self._determine_next_state(conclusions, context)

        # Generate response
        response = self._generate_response(conclusions, context)

        # Record reasoning summary
        self.write_to_scratchpad(f"RESPONSE: {response}")
        self.write_to_scratchpad(f"NEXT STATE: {next_state or 'Same'}")

        return response, next_state, context

    def _extract_facts(self, input_text: str, context: StateContext) -> List[str]:
        """
        Extract relevant facts from input.

        Args:
            input_text: Input text from the user
            context: Current state context

        Returns:
            List of facts
        """
        # Default implementation - override in subclasses
        return [f"User said: {input_text}"]

    def _form_hypotheses(self, facts: List[str], context: StateContext) -> List[str]:
        """
        Form hypotheses based on facts.

        Args:
            facts: List of extracted facts
            context: Current state context

        Returns:
            List of hypotheses
        """
        # Default implementation - override in subclasses
        return ["Default hypothesis based on user input"]

    def _draw_conclusions(
        self, facts: List[str], hypotheses: List[str], context: StateContext
    ) -> List[str]:
        """
        Draw conclusions based on facts and hypotheses.

        Args:
            facts: List of extracted facts
            hypotheses: List of formed hypotheses
            context: Current state context

        Returns:
            List of conclusions
        """
        # Default implementation - override in subclasses
        return ["Default conclusion based on analysis"]

    def _determine_next_state(
        self, conclusions: List[str], context: StateContext
    ) -> Optional[str]:
        """
        Determine the next state based on conclusions.

        Args:
            conclusions: List of conclusions
            context: Current state context

        Returns:
            Name of the next state or None to stay in current state
        """
        # Default implementation - override in subclasses
        return None

    def _generate_response(self, conclusions: List[str], context: StateContext) -> str:
        """
        Generate a response based on conclusions.

        Args:
            conclusions: List of conclusions
            context: Current state context

        Returns:
            Response text
        """
        # Default implementation - override in subclasses
        return "I've processed your input and drawn some conclusions."


# Example implementation
class ProductRecommendationState(ReasoningState):
    """Example implementation for product recommendations."""

    def __init__(self):
        super().__init__(
            name="product_recommendation",
            description="Recommends products based on user preferences",
            allowed_transitions=[
                StateTransition(
                    target_state="checkout", condition="User wants to purchase"
                ),
                StateTransition(
                    target_state="product_details", condition="User wants more info"
                ),
            ],
        )

    def _extract_facts(self, input_text: str, context: StateContext) -> List[str]:
        """Extract product preferences from user input."""
        facts = []

        # Example logic - in a real implementation, this would be more sophisticated
        if "cheap" in input_text.lower() or "affordable" in input_text.lower():
            facts.append("User is price sensitive")

        if "quality" in input_text.lower() or "premium" in input_text.lower():
            facts.append("User values quality")

        if "fast" in input_text.lower() or "quick" in input_text.lower():
            facts.append("User values speed/efficiency")

        return facts

    def _form_hypotheses(self, facts: List[str], context: StateContext) -> List[str]:
        """Form hypotheses about suitable product categories."""
        hypotheses = []

        if "User is price sensitive" in facts:
            hypotheses.append("Budget-friendly products may be suitable")

        if "User values quality" in facts:
            hypotheses.append("Premium products may be suitable despite price")

        if "User values speed/efficiency" in facts:
            hypotheses.append("Products with quick delivery or setup may be preferred")

        # If we have contradictory preferences
        if "User is price sensitive" in facts and "User values quality" in facts:
            hypotheses.append(
                "Mid-range products with good value proposition may be best"
            )

        return hypotheses

    def _draw_conclusions(
        self, facts: List[str], hypotheses: List[str], context: StateContext
    ) -> List[str]:
        """Draw conclusions about specific product recommendations."""
        conclusions = []

        # Example product recommendations based on hypotheses
        if "Budget-friendly products may be suitable" in hypotheses:
            conclusions.append("Recommend economy product line")

        if "Premium products may be suitable despite price" in hypotheses:
            conclusions.append("Recommend premium product line")

        if "Mid-range products with good value proposition may be best" in hypotheses:
            conclusions.append("Recommend mid-range products with high ratings")

        # Add specific product if we can determine a good fit
        if "Recommend economy product line" in conclusions:
            if "User values speed/efficiency" in facts:
                conclusions.append("Specifically recommend EcoFast model X1")
            else:
                conclusions.append("Specifically recommend EcoBasic model B2")

        return conclusions

    def _determine_next_state(
        self, conclusions: List[str], context: StateContext
    ) -> Optional[str]:
        """Determine if we should transition based on recommendations."""
        # If we have specific product recommendations, go to product details
        if any(conc.startswith("Specifically recommend") for conc in conclusions):
            return "product_details"

        return None

    def _generate_response(self, conclusions: List[str], context: StateContext) -> str:
        """Generate a response with product recommendations."""
        # Start with a generic intro
        response = "Based on your preferences, "

        # Add specific recommendations
        specific_recs = [
            c for c in conclusions if c.startswith("Specifically recommend")
        ]
        if specific_recs:
            products = [c.replace("Specifically recommend ", "") for c in specific_recs]
            response += f"I think you'd be interested in {', '.join(products)}. "
        else:
            # Fall back to product lines
            product_lines = []
            if "Recommend economy product line" in conclusions:
                product_lines.append("our economy line")
            if "Recommend premium product line" in conclusions:
                product_lines.append("our premium collection")
            if "Recommend mid-range products with high ratings" in conclusions:
                product_lines.append("our best-value mid-range options")

            if product_lines:
                response += f"I'd recommend checking out {', '.join(product_lines)}. "

        # Add a question to keep the conversation going
        response += "Would you like more specific details about any of these options?"

        return response
