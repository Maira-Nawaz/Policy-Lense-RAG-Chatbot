"""
Interface every chat/generation backend must implement, so rag_pipeline.py can
swap providers without changing call sites. Mirrors embedding_base.py.
"""
from typing import Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class ChatProvider(Protocol):
    def generate(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        **kwargs,
    ) -> Dict:
        """Generate a response for a conversation.

        Args:
            messages: list of {"role": "user"|"assistant", "content": str}, in order.
            system_instruction: optional system-level instruction, kept separate from
                `messages` since providers typically have a dedicated slot for it.

        Returns:
            dict with at least {"text": str, "prompt_tokens": int, "completion_tokens": int}.
        """
        ...
