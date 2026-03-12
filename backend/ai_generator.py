import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
1. **search_course_content** — Search within course lesson content for specific topics or details.
2. **get_course_outline** — Retrieve a course's full outline: title, course link, and every lesson (number + title). Use this for any question about a course's outline, syllabus, structure, table of contents, or lesson list.

Tool Usage:
- You may make up to 2 sequential tool calls per query when chaining is needed (e.g., get a course outline first, then search for content related to a specific lesson). Prefer fewer calls when a single call suffices.
- For outline/syllabus/structure questions → use **get_course_outline**
- For content/topic questions → use **search_course_content**
- When presenting an outline, include the course title, course link, and all lessons with their numbers and titles
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific questions**: Use the appropriate tool first, then answer
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the tool results"

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_tool_execution(response, api_params, tool_manager)
        
        # Return direct response
        return self._extract_text(response)
    
    def _extract_text(self, response) -> str:
        """Extract first text block from a response, with fallback."""
        for block in response.content:
            if block.type == "text":
                return block.text
        return "I wasn't able to fully process your request. Please try rephrasing your question."

    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls across multiple rounds.

        Supports up to MAX_TOOL_ROUNDS sequential tool-calling rounds.
        Messages accumulate across rounds to preserve full context.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        messages = base_params["messages"].copy()
        current_response = initial_response

        for _round in range(self.MAX_TOOL_ROUNDS):
            # Append assistant's tool_use response
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls and collect results
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    try:
                        tool_result = tool_manager.execute_tool(
                            content_block.name,
                            **content_block.input
                        )
                    except Exception as e:
                        tool_result = {"type": "tool_result", "tool_use_id": content_block.id,
                                       "content": str(e), "is_error": True}
                        tool_results.append(tool_result)
                        continue

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })

            # Add tool results as single message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Make next API call — must include tools since messages contain tool_use blocks
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"]
            }
            if "tools" in base_params:
                next_params["tools"] = base_params["tools"]

            current_response = self.client.messages.create(**next_params)

            # If Claude didn't request another tool call, we're done
            if current_response.stop_reason != "tool_use":
                break

        return self._extract_text(current_response)