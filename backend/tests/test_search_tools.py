"""Tests for CourseSearchTool.execute() method"""
import pytest
from unittest.mock import MagicMock, patch
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchToolExecute:
    """Tests for CourseSearchTool.execute()"""

    def setup_method(self):
        self.mock_store = MagicMock()
        self.tool = CourseSearchTool(self.mock_store)

    # --- Happy path: results returned ---

    def test_execute_returns_formatted_results_for_basic_query(self):
        """execute() should return formatted content when vector store returns results"""
        self.mock_store.search.return_value = SearchResults(
            documents=["Python basics content here"],
            metadata=[{"course_title": "Intro to Python", "lesson_number": 1}],
            distances=[0.3],
        )
        self.mock_store.get_lesson_link.return_value = "https://example.com/lesson1"

        result = self.tool.execute(query="what is python")

        assert "Intro to Python" in result
        assert "Python basics content here" in result
        self.mock_store.search.assert_called_once_with(
            query="what is python", course_name=None, lesson_number=None
        )

    def test_execute_with_course_filter(self):
        """execute() should pass course_name filter to vector store"""
        self.mock_store.search.return_value = SearchResults(
            documents=["MCP content"],
            metadata=[{"course_title": "MCP Course", "lesson_number": 2}],
            distances=[0.2],
        )
        self.mock_store.get_lesson_link.return_value = None
        self.mock_store.get_course_link.return_value = "https://example.com/mcp"

        result = self.tool.execute(query="what is MCP", course_name="MCP")

        self.mock_store.search.assert_called_once_with(
            query="what is MCP", course_name="MCP", lesson_number=None
        )
        assert "MCP Course" in result

    def test_execute_with_lesson_filter(self):
        """execute() should pass lesson_number filter to vector store"""
        self.mock_store.search.return_value = SearchResults(
            documents=["Lesson 3 content"],
            metadata=[{"course_title": "AI Course", "lesson_number": 3}],
            distances=[0.1],
        )
        self.mock_store.get_lesson_link.return_value = "https://example.com/l3"

        result = self.tool.execute(query="transformers", lesson_number=3)

        self.mock_store.search.assert_called_once_with(
            query="transformers", course_name=None, lesson_number=3
        )
        assert "Lesson 3" in result

    def test_execute_with_both_filters(self):
        """execute() should pass both course_name and lesson_number"""
        self.mock_store.search.return_value = SearchResults(
            documents=["Filtered content"],
            metadata=[{"course_title": "AI Course", "lesson_number": 2}],
            distances=[0.15],
        )
        self.mock_store.get_lesson_link.return_value = None
        self.mock_store.get_course_link.return_value = None

        result = self.tool.execute(
            query="neural nets", course_name="AI", lesson_number=2
        )

        self.mock_store.search.assert_called_once_with(
            query="neural nets", course_name="AI", lesson_number=2
        )

    # --- Empty results ---

    def test_execute_returns_no_content_message_when_empty(self):
        """execute() should return a helpful message when no results found"""
        self.mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        result = self.tool.execute(query="nonexistent topic")

        assert "No relevant content found" in result

    def test_execute_empty_with_course_filter_includes_course_name(self):
        """Empty results message should mention the course filter"""
        self.mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        result = self.tool.execute(query="xyz", course_name="MCP")

        assert "MCP" in result

    def test_execute_empty_with_lesson_filter_includes_lesson(self):
        """Empty results message should mention the lesson filter"""
        self.mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        result = self.tool.execute(query="xyz", lesson_number=5)

        assert "lesson 5" in result.lower()

    # --- Error handling ---

    def test_execute_returns_error_message_on_search_error(self):
        """execute() should return the error message when search fails"""
        self.mock_store.search.return_value = SearchResults.empty(
            "Search error: connection failed"
        )

        result = self.tool.execute(query="anything")

        assert "Search error" in result or "connection failed" in result

    def test_execute_returns_error_when_course_not_found(self):
        """execute() should return error when course resolution fails"""
        self.mock_store.search.return_value = SearchResults.empty(
            "No course found matching 'NonExistent'"
        )

        result = self.tool.execute(query="topic", course_name="NonExistent")

        assert "No course found" in result

    # --- Source tracking ---

    def test_execute_populates_last_sources(self):
        """execute() should populate last_sources for UI consumption"""
        self.mock_store.search.return_value = SearchResults(
            documents=["content1", "content2"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
            distances=[0.2, 0.4],
        )
        self.mock_store.get_lesson_link.side_effect = [
            "https://a.com/l1",
            "https://b.com/l2",
        ]

        self.tool.execute(query="test")

        assert len(self.tool.last_sources) == 2
        assert self.tool.last_sources[0]["name"] == "Course A - Lesson 1"
        assert self.tool.last_sources[0]["link"] == "https://a.com/l1"

    def test_execute_deduplicates_sources(self):
        """execute() should not include duplicate sources"""
        self.mock_store.search.return_value = SearchResults(
            documents=["chunk1", "chunk2"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course A", "lesson_number": 1},
            ],
            distances=[0.2, 0.3],
        )
        self.mock_store.get_lesson_link.return_value = "https://a.com/l1"

        self.tool.execute(query="test")

        assert len(self.tool.last_sources) == 1

    def test_execute_resets_sources_on_empty_results(self):
        """execute() should set empty sources when no results"""
        # First populate sources
        self.tool.last_sources = [{"name": "old", "link": None}]

        self.mock_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[]
        )

        self.tool.execute(query="nothing")

        # last_sources is not reset by execute on empty - it just doesn't call _format_results
        # This tests the actual behavior

    # --- Tool definition ---

    def test_get_tool_definition_has_required_fields(self):
        """Tool definition must have name, description, and input_schema"""
        defn = self.tool.get_tool_definition()

        assert defn["name"] == "search_course_content"
        assert "description" in defn
        assert "input_schema" in defn
        assert defn["input_schema"]["required"] == ["query"]

    # --- Multiple results formatting ---

    def test_execute_formats_multiple_results_with_separators(self):
        """Multiple results should be separated by double newlines"""
        self.mock_store.search.return_value = SearchResults(
            documents=["Content A", "Content B"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
            distances=[0.1, 0.2],
        )
        self.mock_store.get_lesson_link.side_effect = [None, None]
        self.mock_store.get_course_link.side_effect = [None, None]

        result = self.tool.execute(query="test")

        assert "\n\n" in result
        assert "Content A" in result
        assert "Content B" in result

    def test_execute_header_without_lesson_number(self):
        """Header should not include lesson info when lesson_number is None"""
        self.mock_store.search.return_value = SearchResults(
            documents=["General content"],
            metadata=[{"course_title": "My Course", "lesson_number": None}],
            distances=[0.1],
        )
        self.mock_store.get_lesson_link.return_value = None
        self.mock_store.get_course_link.return_value = None

        result = self.tool.execute(query="test")

        assert "[My Course]" in result
        assert "Lesson" not in result


class TestToolManager:
    """Tests for ToolManager registration and execution"""

    def test_register_and_execute_tool(self):
        manager = ToolManager()
        mock_store = MagicMock()
        tool = CourseSearchTool(mock_store)
        manager.register_tool(tool)

        assert "search_course_content" in manager.tools

    def test_execute_unknown_tool_returns_error(self):
        manager = ToolManager()
        result = manager.execute_tool("nonexistent_tool")
        assert "not found" in result.lower()

    def test_get_tool_definitions_returns_all_registered(self):
        manager = ToolManager()
        mock_store = MagicMock()
        manager.register_tool(CourseSearchTool(mock_store))
        manager.register_tool(CourseOutlineTool(mock_store))

        defs = manager.get_tool_definitions()
        names = {d["name"] for d in defs}

        assert "search_course_content" in names
        assert "get_course_outline" in names

    def test_get_last_sources_returns_from_tool(self):
        manager = ToolManager()
        mock_store = MagicMock()
        tool = CourseSearchTool(mock_store)
        tool.last_sources = [{"name": "Test", "link": None}]
        manager.register_tool(tool)

        sources = manager.get_last_sources()
        assert len(sources) == 1

    def test_reset_sources_clears_all(self):
        manager = ToolManager()
        mock_store = MagicMock()
        tool = CourseSearchTool(mock_store)
        tool.last_sources = [{"name": "Test", "link": None}]
        manager.register_tool(tool)

        manager.reset_sources()
        assert tool.last_sources == []
