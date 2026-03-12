"""Tests for AIGenerator — verifies tool calling, multi-round execution, and response extraction"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from ai_generator import AIGenerator


def _make_text_block(text):
    """Helper to create a mock text content block"""
    block = MagicMock()
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(tool_name, tool_input, tool_id="tool_123"):
    """Helper to create a mock tool_use content block"""
    block = MagicMock()
    block.type = "tool_use"
    block.name = tool_name
    block.input = tool_input
    block.id = tool_id
    return block


class TestAIGeneratorDirectResponse:
    """Tests for when the AI responds directly without tool calls"""

    def setup_method(self):
        with patch("anthropic.Anthropic"):
            self.generator = AIGenerator(api_key="test-key", model="test-model")

    def test_direct_response_returns_text(self):
        """When stop_reason is not tool_use, return the text directly"""
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [_make_text_block("Hello! How can I help?")]

        self.generator.client.messages.create.return_value = mock_response

        result = self.generator.generate_response(query="hello")

        assert result == "Hello! How can I help?"

    def test_direct_response_without_tools(self):
        """When no tools provided, API should be called without tools param"""
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [_make_text_block("General answer")]

        self.generator.client.messages.create.return_value = mock_response

        result = self.generator.generate_response(query="what is AI?")

        call_kwargs = self.generator.client.messages.create.call_args[1]
        assert "tools" not in call_kwargs

    def test_conversation_history_included_in_system(self):
        """When conversation_history is provided, it should be in the system prompt"""
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [_make_text_block("Follow-up answer")]

        self.generator.client.messages.create.return_value = mock_response

        self.generator.generate_response(
            query="tell me more",
            conversation_history="User: what is python?\nAssistant: Python is a language.",
        )

        call_kwargs = self.generator.client.messages.create.call_args[1]
        assert "Previous conversation" in call_kwargs["system"]
        assert "what is python?" in call_kwargs["system"]


class TestAIGeneratorToolCalling:
    """Tests for when the AI decides to call the search tool"""

    def setup_method(self):
        with patch("anthropic.Anthropic"):
            self.generator = AIGenerator(api_key="test-key", model="test-model")
        self.mock_tool_manager = MagicMock()

    def test_calls_search_tool_when_stop_reason_is_tool_use(self):
        """When Claude returns tool_use, the generator should execute the tool"""
        # First API call: Claude wants to use a tool
        tool_block = _make_tool_use_block(
            "search_course_content",
            {"query": "what is MCP"},
        )
        initial_response = MagicMock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [tool_block]

        # Second API call: Claude synthesizes final answer
        final_response = MagicMock()
        final_response.stop_reason = "end_turn"
        final_response.content = [_make_text_block("MCP is a protocol for...")]

        self.generator.client.messages.create.side_effect = [
            initial_response,
            final_response,
        ]
        self.mock_tool_manager.execute_tool.return_value = "MCP content from vector store"

        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]

        result = self.generator.generate_response(
            query="what is MCP",
            tools=tools,
            tool_manager=self.mock_tool_manager,
        )

        # Verify tool was executed
        self.mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="what is MCP"
        )
        assert result == "MCP is a protocol for..."

    def test_tool_result_sent_back_to_claude(self):
        """The tool result should be sent back to Claude in a follow-up message"""
        tool_block = _make_tool_use_block(
            "search_course_content",
            {"query": "RAG"},
            tool_id="tool_abc",
        )
        initial_response = MagicMock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [tool_block]

        final_response = MagicMock()
        final_response.stop_reason = "end_turn"
        final_response.content = [_make_text_block("RAG explanation")]

        self.generator.client.messages.create.side_effect = [
            initial_response,
            final_response,
        ]
        self.mock_tool_manager.execute_tool.return_value = "RAG search results"

        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]

        self.generator.generate_response(
            query="what is RAG",
            tools=tools,
            tool_manager=self.mock_tool_manager,
        )

        # Check the second API call includes tool results
        second_call_kwargs = self.generator.client.messages.create.call_args_list[1][1]
        messages = second_call_kwargs["messages"]

        # Should have: user msg, assistant tool_use, user tool_result
        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

        # The tool result message
        tool_result_content = messages[2]["content"]
        assert tool_result_content[0]["type"] == "tool_result"
        assert tool_result_content[0]["tool_use_id"] == "tool_abc"
        assert tool_result_content[0]["content"] == "RAG search results"

    def test_no_tool_execution_without_tool_manager(self):
        """If tool_manager is None, tool_use response should be returned as-is"""
        tool_block = _make_tool_use_block(
            "search_course_content",
            {"query": "test"},
        )
        text_block = _make_text_block("I'll search for that.")

        initial_response = MagicMock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [text_block, tool_block]

        self.generator.client.messages.create.return_value = initial_response

        # No tool_manager → should return text from _extract_text
        result = self.generator.generate_response(query="test", tools=[{}])

        assert result == "I'll search for that."

    def test_tools_param_included_in_api_call(self):
        """When tools are provided, they should be in the API call"""
        mock_response = MagicMock()
        mock_response.stop_reason = "end_turn"
        mock_response.content = [_make_text_block("Direct answer")]

        self.generator.client.messages.create.return_value = mock_response

        tools = [
            {"name": "search_course_content", "description": "Search courses", "input_schema": {}},
            {"name": "get_course_outline", "description": "Get outline", "input_schema": {}},
        ]

        self.generator.generate_response(query="test", tools=tools)

        call_kwargs = self.generator.client.messages.create.call_args[1]
        assert call_kwargs["tools"] == tools
        assert call_kwargs["tool_choice"] == {"type": "auto"}

    def test_follow_up_api_calls_include_tools(self):
        """Follow-up API calls MUST include tools — Anthropic API requires tool
        definitions when messages contain tool_use content blocks."""
        tool_block = _make_tool_use_block(
            "search_course_content", {"query": "test"}
        )
        initial_response = MagicMock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [tool_block]

        final_response = MagicMock()
        final_response.stop_reason = "end_turn"
        final_response.content = [_make_text_block("Final answer")]

        self.generator.client.messages.create.side_effect = [
            initial_response,
            final_response,
        ]
        self.mock_tool_manager.execute_tool.return_value = "tool output"

        tools = [{"name": "search_course_content", "description": "Search", "input_schema": {}}]
        self.generator.generate_response(
            query="test", tools=tools, tool_manager=self.mock_tool_manager
        )

        second_call_kwargs = self.generator.client.messages.create.call_args_list[1][1]
        assert "tools" in second_call_kwargs, (
            "BUG: Second API call is missing 'tools' — Anthropic API will reject "
            "requests that contain tool_use blocks without tool definitions"
        )

    def test_handles_multiple_tool_calls_in_one_response(self):
        """If Claude returns multiple tool_use blocks, all should be executed"""
        tool_block1 = _make_tool_use_block(
            "search_course_content", {"query": "MCP"}, tool_id="t1"
        )
        tool_block2 = _make_tool_use_block(
            "get_course_outline", {"course_name": "MCP"}, tool_id="t2"
        )
        initial_response = MagicMock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [tool_block1, tool_block2]

        final_response = MagicMock()
        final_response.stop_reason = "end_turn"
        final_response.content = [_make_text_block("Combined answer")]

        self.generator.client.messages.create.side_effect = [
            initial_response,
            final_response,
        ]
        self.mock_tool_manager.execute_tool.side_effect = ["result1", "result2"]

        tools = [
            {"name": "search_course_content", "description": "Search", "input_schema": {}},
            {"name": "get_course_outline", "description": "Outline", "input_schema": {}},
        ]

        result = self.generator.generate_response(
            query="tell me about MCP", tools=tools, tool_manager=self.mock_tool_manager
        )

        assert self.mock_tool_manager.execute_tool.call_count == 2
        assert result == "Combined answer"


class TestMultiRoundToolCalling:
    """Tests for sequential multi-round tool calling (max 2 rounds)"""

    def setup_method(self):
        with patch("anthropic.Anthropic"):
            self.generator = AIGenerator(api_key="test-key", model="test-model")
        self.mock_tool_manager = MagicMock()
        self.tools = [
            {"name": "search_course_content", "description": "Search", "input_schema": {}},
            {"name": "get_course_outline", "description": "Outline", "input_schema": {}},
        ]

    def test_two_sequential_tool_rounds(self):
        """Claude chains two tool calls: outline → search. 3 API calls, 2 tool executions."""
        # Round 0: initial → tool_use (get_course_outline)
        r1 = MagicMock()
        r1.stop_reason = "tool_use"
        r1.content = [_make_tool_use_block("get_course_outline", {"course_name": "AI"}, "t1")]

        # Round 1: follow-up → tool_use (search_course_content)
        r2 = MagicMock()
        r2.stop_reason = "tool_use"
        r2.content = [_make_tool_use_block("search_course_content", {"query": "lesson 3 details"}, "t2")]

        # Round 2 (after max rounds): final text
        r3 = MagicMock()
        r3.stop_reason = "end_turn"
        r3.content = [_make_text_block("Here are the details about lesson 3.")]

        self.generator.client.messages.create.side_effect = [r1, r2, r3]
        self.mock_tool_manager.execute_tool.side_effect = ["outline data", "lesson 3 content"]

        result = self.generator.generate_response(
            query="What does lesson 3 of the AI course cover?",
            tools=self.tools,
            tool_manager=self.mock_tool_manager,
        )

        assert self.generator.client.messages.create.call_count == 3
        assert self.mock_tool_manager.execute_tool.call_count == 2
        assert result == "Here are the details about lesson 3."

    def test_max_rounds_enforced(self):
        """If Claude keeps requesting tools, loop stops after MAX_TOOL_ROUNDS."""
        # All responses request tool_use — should only get initial + 2 rounds = 3 calls
        responses = []
        for i in range(3):
            r = MagicMock()
            r.stop_reason = "tool_use"
            r.content = [_make_tool_use_block("search_course_content", {"query": f"q{i}"}, f"t{i}")]
            responses.append(r)

        self.generator.client.messages.create.side_effect = responses
        self.mock_tool_manager.execute_tool.return_value = "some result"

        result = self.generator.generate_response(
            query="deep search",
            tools=self.tools,
            tool_manager=self.mock_tool_manager,
        )

        # initial call + MAX_TOOL_ROUNDS follow-ups = 3 total
        assert self.generator.client.messages.create.call_count == 3
        # Last response had no text block → fallback
        assert "wasn't able to fully process" in result

    def test_tool_error_sends_is_error_result(self):
        """Tool execution errors are caught and sent as is_error=True results."""
        tool_block = _make_tool_use_block("search_course_content", {"query": "bad"}, "t1")
        initial_response = MagicMock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [tool_block]

        final_response = MagicMock()
        final_response.stop_reason = "end_turn"
        final_response.content = [_make_text_block("Sorry, the search failed.")]

        self.generator.client.messages.create.side_effect = [initial_response, final_response]
        self.mock_tool_manager.execute_tool.side_effect = RuntimeError("connection timeout")

        result = self.generator.generate_response(
            query="search something",
            tools=self.tools,
            tool_manager=self.mock_tool_manager,
        )

        # Should not crash
        assert result == "Sorry, the search failed."

        # Verify the error result was sent to Claude with is_error
        second_call_kwargs = self.generator.client.messages.create.call_args_list[1][1]
        tool_results = second_call_kwargs["messages"][2]["content"]
        assert tool_results[0]["is_error"] is True
        assert "connection timeout" in tool_results[0]["content"]

    def test_message_accumulation_across_rounds(self):
        """In a 2-round flow, the 3rd API call's messages should have 5 entries:
        user, assistant, tool_result, assistant, tool_result."""
        r1 = MagicMock()
        r1.stop_reason = "tool_use"
        r1.content = [_make_tool_use_block("get_course_outline", {"course_name": "X"}, "t1")]

        r2 = MagicMock()
        r2.stop_reason = "tool_use"
        r2.content = [_make_tool_use_block("search_course_content", {"query": "Y"}, "t2")]

        r3 = MagicMock()
        r3.stop_reason = "end_turn"
        r3.content = [_make_text_block("Final")]

        self.generator.client.messages.create.side_effect = [r1, r2, r3]
        self.mock_tool_manager.execute_tool.side_effect = ["outline", "content"]

        self.generator.generate_response(
            query="chain query",
            tools=self.tools,
            tool_manager=self.mock_tool_manager,
        )

        third_call_kwargs = self.generator.client.messages.create.call_args_list[2][1]
        messages = third_call_kwargs["messages"]
        assert len(messages) == 5
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"  # tool_result round 1
        assert messages[3]["role"] == "assistant"
        assert messages[4]["role"] == "user"  # tool_result round 2

    def test_early_termination_after_one_round(self):
        """If Claude returns text after one tool round, loop exits early (regression test)."""
        tool_block = _make_tool_use_block("search_course_content", {"query": "test"}, "t1")
        initial_response = MagicMock()
        initial_response.stop_reason = "tool_use"
        initial_response.content = [tool_block]

        final_response = MagicMock()
        final_response.stop_reason = "end_turn"
        final_response.content = [_make_text_block("Single round answer")]

        self.generator.client.messages.create.side_effect = [initial_response, final_response]
        self.mock_tool_manager.execute_tool.return_value = "result"

        result = self.generator.generate_response(
            query="simple query",
            tools=self.tools,
            tool_manager=self.mock_tool_manager,
        )

        assert self.generator.client.messages.create.call_count == 2
        assert self.mock_tool_manager.execute_tool.call_count == 1
        assert result == "Single round answer"


class TestExtractText:
    """Tests for the _extract_text helper"""

    def setup_method(self):
        with patch("anthropic.Anthropic"):
            self.generator = AIGenerator(api_key="test-key", model="test-model")

    def test_extract_text_fallback_when_no_text_block(self):
        """Response with only tool_use blocks returns fallback message."""
        response = MagicMock()
        response.content = [_make_tool_use_block("search_course_content", {"query": "x"}, "t1")]

        result = self.generator._extract_text(response)

        assert result == "I wasn't able to fully process your request. Please try rephrasing your question."

    def test_extract_text_returns_first_text_block(self):
        """When multiple text blocks exist, return the first one."""
        response = MagicMock()
        response.content = [
            _make_tool_use_block("search_course_content", {"query": "x"}, "t1"),
            _make_text_block("First text"),
            _make_text_block("Second text"),
        ]

        result = self.generator._extract_text(response)

        assert result == "First text"


class TestAIGeneratorSystemPrompt:
    """Tests for the system prompt configuration"""

    def test_system_prompt_mentions_search_tool(self):
        assert "search_course_content" in AIGenerator.SYSTEM_PROMPT

    def test_system_prompt_mentions_outline_tool(self):
        assert "get_course_outline" in AIGenerator.SYSTEM_PROMPT

    def test_system_prompt_allows_multiple_tool_calls(self):
        """Prompt should no longer restrict to one tool call per query."""
        assert "One tool call per query maximum" not in AIGenerator.SYSTEM_PROMPT

    def test_max_tool_rounds_constant(self):
        assert AIGenerator.MAX_TOOL_ROUNDS == 2

    def test_base_params_include_model_and_temperature(self):
        with patch("anthropic.Anthropic"):
            gen = AIGenerator(api_key="key", model="claude-test")

        assert gen.base_params["model"] == "claude-test"
        assert gen.base_params["temperature"] == 0
        assert gen.base_params["max_tokens"] == 800
