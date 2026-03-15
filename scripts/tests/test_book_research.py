"""Tests for the book research agent.

Run: cd scripts && python -m pytest tests/test_book_research.py -v

These tests hit real Gemini APIs (require GEMINI_KEY).
Use --skip-live to skip API-dependent tests.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Add scripts dir to path
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

SKIP_LIVE = not (os.environ.get('GEMINI_API_KEY') or os.environ.get('GEMINI_KEY'))
SKIP_MSG = "No GEMINI_API_KEY set — skipping live API tests"

DATA_DIR = SCRIPT_DIR / 'data'
BOOK_RESEARCH_DIR = DATA_DIR / 'book_research'


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Remove test research files after each test."""
    yield
    for p in BOOK_RESEARCH_DIR.glob('test_*.json'):
        p.unlink(missing_ok=True)


# --- Unit tests (no API calls) ---

class TestParseJson:
    def test_plain_json(self):
        from book_research_agent import _parse_json
        result = _parse_json('{"key": "value"}')
        assert result == {'key': 'value'}

    def test_markdown_fenced_json(self):
        from book_research_agent import _parse_json
        result = _parse_json('```json\n{"key": "value"}\n```')
        assert result == {'key': 'value'}

    def test_json_with_preamble(self):
        from book_research_agent import _parse_json
        result = _parse_json('Here is the JSON:\n{"key": "value"}\n\nDone.')
        assert result == {'key': 'value'}

    def test_json_array(self):
        from book_research_agent import _parse_json
        result = _parse_json('[{"a": 1}, {"b": 2}]')
        assert isinstance(result, list)
        assert len(result) == 2

    def test_empty_input(self):
        from book_research_agent import _parse_json
        assert _parse_json('') is None
        assert _parse_json(None) is None

    def test_invalid_json(self):
        from book_research_agent import _parse_json
        assert _parse_json('not json at all') is None


class TestArticleConnections:
    def test_finds_matching_topics(self):
        from book_research_agent import _find_article_connections
        articles = [
            {'id': 'a1', 'title': 'Art 1', 'topics': ['medieval history', 'trade']},
            {'id': 'a2', 'title': 'Art 2', 'topics': ['quantum physics']},
            {'id': 'a3', 'title': 'Art 3', 'topics': ['trade', 'economics']},
        ]
        book_topics = ['trade', 'maritime commerce']
        conns = _find_article_connections(book_topics, articles)
        assert len(conns) == 2
        assert conns[0]['article_id'] in ('a1', 'a3')

    def test_empty_topics(self):
        from book_research_agent import _find_article_connections
        conns = _find_article_connections([], [{'id': 'a1', 'topics': ['x']}])
        assert conns == []

    def test_no_matches(self):
        from book_research_agent import _find_article_connections
        articles = [{'id': 'a1', 'title': 'Art', 'topics': ['quantum']}]
        conns = _find_article_connections(['medieval'], articles)
        assert conns == []

    def test_respects_max(self):
        from book_research_agent import _find_article_connections
        articles = [{'id': f'a{i}', 'title': f'Art {i}', 'topics': ['x']} for i in range(20)]
        conns = _find_article_connections(['x'], articles, max_connections=5)
        assert len(conns) == 5


class TestGetAllBookClaims:
    def test_collects_from_research_files(self, tmp_path):
        from book_research_agent import get_all_book_claims, BOOK_RESEARCH_DIR

        # Write a test research file
        test_research = {
            'book_id': 'test_claims',
            'title': 'Test Book',
            'chapter_research': {
                '1': {'summary': 'Ch 1', 'claims': ['Claim A', 'Claim B'], 'key_terms': []},
                '2': {'summary': 'Ch 2', 'claims': ['Claim C'], 'key_terms': []},
            }
        }
        (BOOK_RESEARCH_DIR / 'test_claims.json').write_text(json.dumps(test_research))

        claims = get_all_book_claims()
        test_claims = [c for c in claims if c['book_id'] == 'test_claims']
        assert len(test_claims) == 3
        assert test_claims[0]['text'] == 'Claim A'
        assert test_claims[0]['chapter_number'] == '1'
        assert test_claims[0]['source'] == 'research'


# --- Live API tests ---

@pytest.mark.skipif(SKIP_LIVE, reason=SKIP_MSG)
class TestResearchBookLive:
    def test_research_machiavelli(self):
        from book_research_agent import research_book

        result = research_book(
            'test_machiavelli', 'The Prince', 'Niccolò Machiavelli',
            None,
            [{'number': 1, 'title': 'How Many Kinds of Principalities There Are'},
             {'number': 15, 'title': 'Of Things for Which Men Are Praised or Blamed'},
             {'number': 25, 'title': 'How Much Fortune Can Do'}],
            ['political philosophy', 'leadership', 'Italian Renaissance'],
        )

        assert result['thesis'], "Thesis should not be empty"
        assert 'prince' in result['thesis'].lower() or 'political' in result['thesis'].lower() or 'machiavelli' in result['thesis'].lower()
        assert len(result['chapter_research']) >= 1, "Should have at least 1 chapter researched"

        # Check chapter structure
        for ch_num, ch_data in result['chapter_research'].items():
            assert ch_data.get('summary'), f"Chapter {ch_num} should have a summary"
            assert len(ch_data.get('claims', [])) >= 1, f"Chapter {ch_num} should have claims"

        # Check suggested reading exists
        assert len(result['suggested_reading']) >= 1, "Should suggest at least 1 reading"

        # Verify file was saved
        assert (BOOK_RESEARCH_DIR / 'test_machiavelli.json').exists()

    def test_research_pirenne(self):
        """Test with a book whose topics should match existing articles."""
        from book_research_agent import research_book

        result = research_book(
            'test_pirenne', 'Mohammed and Charlemagne', 'Henri Pirenne',
            None,
            [{'number': 1, 'title': 'Mediterranean Commerce in the Roman Empire'}],
            ['medieval history', 'Mediterranean', 'Islam', 'trade'],
        )

        assert result['thesis']
        assert len(result['chapter_research']) >= 1


@pytest.mark.skipif(SKIP_LIVE, reason=SKIP_MSG)
class TestChapterInsightsLive:
    def test_chapter_insights_new_chapter(self):
        """Test getting insights for a chapter that hasn't been researched yet."""
        from book_research_agent import get_chapter_insights

        # First create a minimal research file
        BOOK_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
        (BOOK_RESEARCH_DIR / 'test_insights.json').write_text(json.dumps({
            'book_id': 'test_insights',
            'title': 'The Prince',
            'author': 'Machiavelli',
            'thesis': 'Political power requires pragmatism over virtue.',
            'chapter_research': {},
            'article_connections': [],
        }))

        result = get_chapter_insights('test_insights', 15, 'Of Things for Which Men Are Praised or Blamed')

        assert result['summary'], "Should have a summary"
        assert len(result['claims']) >= 1, "Should have claims"
        assert result['chapter_number'] == 15


@pytest.mark.skipif(SKIP_LIVE, reason=SKIP_MSG)
class TestStorySoFarLive:
    def test_story_so_far_with_research(self):
        from book_research_agent import generate_story_so_far

        # Create a research file with chapter data
        BOOK_RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
        (BOOK_RESEARCH_DIR / 'test_story.json').write_text(json.dumps({
            'book_id': 'test_story',
            'title': 'The Prince',
            'author': 'Machiavelli',
            'thesis': 'Effective rulers must learn how not to be good.',
            'chapter_research': {
                '1': {'summary': 'Types of principalities and how they are acquired.', 'claims': [], 'key_terms': []},
                '15': {'summary': 'Rulers must sometimes act against moral virtue.', 'claims': [], 'key_terms': []},
            },
            'suggested_reading': [{'title': 'Discourses on Livy', 'url': '', 'reason': 'Complementary work'}],
        }))

        result = generate_story_so_far(
            'test_story', 'The Prince', 'Machiavelli',
            'Chapter 15', 89, 140,
            [{'text': 'Fortune is the arbiter of half our actions', 'chapter': 'Chapter 25'}],
        )

        assert result['argument_summary'], "Should have an argument summary"
        assert 'suggested_reading' in result

    def test_story_so_far_without_research(self):
        from book_research_agent import generate_story_so_far

        result = generate_story_so_far(
            'test_nodata', 'Unknown Book', 'Unknown Author',
            'Chapter 3', 50, 200,
        )

        assert result['argument_summary'], "Should still produce something"


# --- Endpoint tests (require running server) ---

@pytest.mark.skipif(True, reason="Requires running server — enable manually")
class TestEndpoints:
    BASE = 'http://localhost:8090'

    def test_book_research_endpoint(self):
        import requests
        r = requests.post(f'{self.BASE}/book/research', json={
            'book_id': 'test_endpoint',
            'title': 'The Prince',
            'author': 'Niccolò Machiavelli',
            'chapters': [{'number': 1, 'title': 'Types of Principalities'}],
            'topics': ['political philosophy'],
        })
        assert r.status_code in (200, 202)

    def test_story_so_far_endpoint(self):
        import requests
        r = requests.post(f'{self.BASE}/book/story-so-far', json={
            'book_id': 'test_endpoint',
            'title': 'The Prince',
            'author': 'Machiavelli',
            'current_chapter': 'Chapter 15',
            'current_page': 89,
            'page_count': 140,
            'captures': [],
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get('argument_summary')

    def test_chapter_insights_endpoint(self):
        import requests
        r = requests.post(f'{self.BASE}/book/chapter-insights', json={
            'book_id': 'test_endpoint',
            'chapter_number': 15,
            'chapter_title': 'Of Things for Which Men Are Praised or Blamed',
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get('summary')

    def test_get_research_endpoint(self):
        import requests
        r = requests.get(f'{self.BASE}/book/research/test_endpoint')
        # May be 404 if research hasn't completed yet
        assert r.status_code in (200, 404)
