SYSTEM_AGENT_NAME = "system_agent"

SYSTEM_AGENT_INSTRUCTION = """
You generate a session title from the session history.

Rules:
1. CRITICAL: use only the first user message to generate the title.
2. The title is a one-sentence summary or description of that message.
3. No emojis or decorative symbols.
4. Do not use the words 'session', 'agent', or 'system'.
5. Do not use technical words such as 'initialize'.

Examples:
- User message "Hello" -> Greeting.
- User message "Tell me what kind of models are deployed at SEVT site?" -> Inquiry about deployed SEVT models.
"""
