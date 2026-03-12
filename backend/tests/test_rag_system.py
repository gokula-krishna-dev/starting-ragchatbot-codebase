"""Tests for RAGSystem.query() — the full pipeline for content queries"""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from rag_system import RAGSystem
from vector_store import SearchResults


@pytest.fixture
def mock_config():
    config = MagicMock()
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.CHROMA_PATH = "/tmp/test_chroma"
    config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"
    config.MAX_RESULTS = 5
    config.ANTHROPIC_API_KEY = "test-key"
    config.ANTHROPIC_MODEL = "test-model"
    config.MAX_HISTORY = 2
    return config


@pytest.fixture
def rag_system(mock_config):
    """Create a RAGSystem with all dependencies mocked"""
    with patch("rag_system.DocumentProcessor"), \
         patch("rag_system.VectorStore") as MockVS, \
         patch("rag_system.AIGenerator") as MockAI, \
         patch("rag_system.SessionManager") as MockSM:

        system = RAGSystem(mock_config)

        # Expose mocks for assertions
        system._mock_vector_store = MockVS.return_value
        system._mock_ai_generator = MockAI.return_value
        system._mock_session_manager = MockSM.return_value

        yield system


class TestRAGSystemQuery:
    """Tests for the query pipeline"""

    def test_query_returns_response_and_sources(self, rag_system):
        """query() should return a (response, sources) tuple"""
        rag_system._mock_ai_generator.generate_response.return_value = "Test answer"
        rag_system._mock_session_manager.get_conversation_history.return_value = None

        response, sources = rag_system.query("what is python?")

        assert response == "Test answer"
        assert isinstance(sources, list)

    def test_query_passes_tools_to_ai_generator(self, rag_system):
        """query() should pass tool definitions to the AI generator"""
        rag_system._mock_ai_generator.generate_response.return_value = "Answer"
        rag_system._mock_session_manager.get_conversation_history.return_value = None

        rag_system.query("test question")

        call_kwargs = rag_system._mock_ai_generator.generate_response.call_args[1]
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] is not None

    def test_query_passes_tool_manager_to_ai_generator(self, rag_system):
        """query() should pass tool_manager so AI can execute tools"""
        rag_system._mock_ai_generator.generate_response.return_value = "Answer"
        rag_system._mock_session_manager.get_conversation_history.return_value = None

        rag_system.query("test question")

        call_kwargs = rag_system._mock_ai_generator.generate_response.call_args[1]
        assert "tool_manager" in call_kwargs
        assert call_kwargs["tool_manager"] is not None

    def test_query_wraps_user_input_in_prompt(self, rag_system):
        """query() should wrap the user query in a prompt template"""
        rag_system._mock_ai_generator.generate_response.return_value = "Answer"
        rag_system._mock_session_manager.get_conversation_history.return_value = None

        rag_system.query("what is MCP?")

        call_kwargs = rag_system._mock_ai_generator.generate_response.call_args[1]
        assert "what is MCP?" in call_kwargs["query"]

    def test_query_includes_session_history(self, rag_system):
        """query() should include conversation history when session exists"""
        rag_system._mock_session_manager.get_conversation_history.return_value = (
            "User: hi\nAssistant: hello"
        )
        rag_system._mock_ai_generator.generate_response.return_value = "Follow-up answer"

        rag_system.query("tell me more", session_id="session_1")

        call_kwargs = rag_system._mock_ai_generator.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] == "User: hi\nAssistant: hello"

    def test_query_without_session_passes_none_history(self, rag_system):
        """query() without session_id should pass None for history"""
        rag_system._mock_session_manager.get_conversation_history.return_value = None
        rag_system._mock_ai_generator.generate_response.return_value = "Answer"

        rag_system.query("question")

        call_kwargs = rag_system._mock_ai_generator.generate_response.call_args[1]
        assert call_kwargs["conversation_history"] is None

    def test_query_updates_session_history(self, rag_system):
        """query() should save the exchange to session history"""
        rag_system._mock_ai_generator.generate_response.return_value = "The answer"
        rag_system._mock_session_manager.get_conversation_history.return_value = None

        rag_system.query("my question", session_id="session_1")

        rag_system._mock_session_manager.add_exchange.assert_called_once()
        args = rag_system._mock_session_manager.add_exchange.call_args[0]
        assert args[0] == "session_1"
        # The query is wrapped in a prompt
        assert "my question" in args[1]
        assert args[2] == "The answer"

    def test_query_retrieves_and_resets_sources(self, rag_system):
        """query() should get sources from tool_manager then reset them"""
        rag_system._mock_ai_generator.generate_response.return_value = "Answer"
        rag_system._mock_session_manager.get_conversation_history.return_value = None

        # Manually set sources on the actual tool
        rag_system.search_tool.last_sources = [
            {"name": "Course A - Lesson 1", "link": "https://example.com"}
        ]

        response, sources = rag_system.query("test")

        assert len(sources) == 1
        assert sources[0]["name"] == "Course A - Lesson 1"
        # Sources should be reset after retrieval
        assert rag_system.search_tool.last_sources == []


class TestRAGSystemToolIntegration:
    """Tests verifying that tool_manager is wired correctly"""

    def test_search_tool_is_registered(self, rag_system):
        """CourseSearchTool should be registered in tool_manager"""
        assert "search_course_content" in rag_system.tool_manager.tools

    def test_outline_tool_is_registered(self, rag_system):
        """CourseOutlineTool should be registered in tool_manager"""
        assert "get_course_outline" in rag_system.tool_manager.tools

    def test_tool_definitions_are_valid(self, rag_system):
        """Tool definitions should have required Anthropic API fields"""
        defs = rag_system.tool_manager.get_tool_definitions()

        for tool_def in defs:
            assert "name" in tool_def
            assert "description" in tool_def
            assert "input_schema" in tool_def

    def test_tool_manager_can_execute_search(self, rag_system):
        """tool_manager.execute_tool should delegate to CourseSearchTool"""
        # Mock the underlying vector store search
        rag_system.search_tool.store = MagicMock()
        rag_system.search_tool.store.search.return_value = SearchResults(
            documents=["test content"],
            metadata=[{"course_title": "Test", "lesson_number": 1}],
            distances=[0.1],
        )
        rag_system.search_tool.store.get_lesson_link.return_value = None
        rag_system.search_tool.store.get_course_link.return_value = None

        result = rag_system.tool_manager.execute_tool(
            "search_course_content", query="test query"
        )

        assert "test content" in result


class TestRAGSystemErrorHandling:
    """Tests for error scenarios in the query pipeline"""

    def test_query_propagates_ai_generator_exception(self, rag_system):
        """If AI generator raises, query() should let it propagate"""
        rag_system._mock_ai_generator.generate_response.side_effect = Exception(
            "API error"
        )
        rag_system._mock_session_manager.get_conversation_history.return_value = None

        with pytest.raises(Exception, match="API error"):
            rag_system.query("test")

    def test_query_handles_empty_tool_results_gracefully(self, rag_system):
        """When tools return no sources, sources list should be empty"""
        rag_system._mock_ai_generator.generate_response.return_value = "No results found"
        rag_system._mock_session_manager.get_conversation_history.return_value = None

        response, sources = rag_system.query("obscure topic")

        assert response == "No results found"
        assert sources == []
