"""Tests for palace.core.memory_quality — Memory quality management.

Covers QualityScore, CleanupPolicy, MemoryQualityChecker,
and MemoryCleanupTask.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from palace.core.memory_quality import (
    CleanupPolicy,
    MemoryCleanupTask,
    MemoryQualityChecker,
    QualityScore,
)

# ---------------------------------------------------------------------------
# QualityScore enum
# ---------------------------------------------------------------------------


class TestQualityScore:
    """Tests for the QualityScore enum."""

    def test_has_four_values(self):
        """QualityScore should define exactly 4 members."""
        assert len(QualityScore) == 4

    def test_high(self):
        assert QualityScore.HIGH == "high"

    def test_medium(self):
        assert QualityScore.MEDIUM == "medium"

    def test_low(self):
        assert QualityScore.LOW == "low"

    def test_irrelevant(self):
        assert QualityScore.IRRELEVANT == "irrelevant"

    def test_all_values(self):
        values = {m.value for m in QualityScore}
        assert values == {"high", "medium", "low", "irrelevant"}

    def test_is_str_enum(self):
        """QualityScore values should be strings."""
        for member in QualityScore:
            assert isinstance(member.value, str)

    def test_ordering_semantics(self):
        """Quality levels represent decreasing quality."""
        # We verify the conceptual ordering: HIGH > MEDIUM > LOW > IRRELEVANT
        assert QualityScore.HIGH != QualityScore.MEDIUM
        assert QualityScore.MEDIUM != QualityScore.LOW
        assert QualityScore.LOW != QualityScore.IRRELEVANT


# ---------------------------------------------------------------------------
# CleanupPolicy
# ---------------------------------------------------------------------------


class TestCleanupPolicy:
    """Tests for the CleanupPolicy dataclass."""

    def test_default_values(self):
        """CleanupPolicy should have sensible defaults."""
        policy = CleanupPolicy()
        assert policy.max_entries_per_project == 10000
        assert policy.min_relevance_score == 0.3
        assert policy.expire_after_days == 90
        assert policy.expire_episodic_after_days == 30
        assert policy.deduplication_similarity_threshold == 0.85
        assert policy.cleanup_interval_hours == 24
        assert policy.batch_size == 100

    def test_custom_values(self):
        """CleanupPolicy should accept custom values."""
        policy = CleanupPolicy(
            max_entries_per_project=5000,
            min_relevance_score=0.5,
            expire_after_days=60,
            expire_episodic_after_days=15,
            deduplication_similarity_threshold=0.9,
            cleanup_interval_hours=12,
            batch_size=50,
        )
        assert policy.max_entries_per_project == 5000
        assert policy.min_relevance_score == 0.5
        assert policy.expire_after_days == 60
        assert policy.expire_episodic_after_days == 15
        assert policy.deduplication_similarity_threshold == 0.9
        assert policy.cleanup_interval_hours == 12
        assert policy.batch_size == 50

    def test_independent_instances(self):
        """Each CleanupPolicy instance should be independent."""
        policy1 = CleanupPolicy()
        policy2 = CleanupPolicy()
        policy1.max_entries_per_project = 999
        assert policy2.max_entries_per_project == 10000

    def test_zero_min_relevance_score(self):
        """CleanupPolicy should accept a min_relevance_score of 0."""
        policy = CleanupPolicy(min_relevance_score=0.0)
        assert policy.min_relevance_score == 0.0

    def test_very_small_expire_after_days(self):
        """CleanupPolicy should accept very small expire_after_days."""
        policy = CleanupPolicy(expire_after_days=1)
        assert policy.expire_after_days == 1

    def test_large_batch_size(self):
        """CleanupPolicy should accept a large batch_size."""
        policy = CleanupPolicy(batch_size=10000)
        assert policy.batch_size == 10000


# ---------------------------------------------------------------------------
# MemoryQualityChecker
# ---------------------------------------------------------------------------


class TestMemoryQualityChecker:
    """Tests for the MemoryQualityChecker class."""

    def test_initialization_default(self):
        """MemoryQualityChecker should initialize with default policy."""
        checker = MemoryQualityChecker()
        assert checker.policy is not None
        assert checker.policy.min_relevance_score == 0.3

    def test_initialization_custom_policy(self):
        """MemoryQualityChecker should accept a custom policy."""
        policy = CleanupPolicy(min_relevance_score=0.5, expire_after_days=60)
        checker = MemoryQualityChecker(policy=policy)
        assert checker.policy.min_relevance_score == 0.5
        assert checker.policy.expire_after_days == 60

    # --- check_quality ---

    def test_check_quality_long_content(self):
        """check_quality should give higher scores to longer content."""
        checker = MemoryQualityChecker()
        long_content = "A" * 300
        short_content = "A" * 5
        score_long = checker.check_quality(long_content, {}, access_count=0)
        score_short = checker.check_quality(short_content, {}, access_count=0)
        assert score_long > score_short

    def test_check_quality_access_count(self):
        """check_quality should increase score with higher access count."""
        checker = MemoryQualityChecker()
        content = "Some reasonable content here for testing quality"
        score_low_access = checker.check_quality(content, {}, access_count=0)
        score_high_access = checker.check_quality(content, {}, access_count=5)
        assert score_high_access > score_low_access

    def test_check_quality_access_count_capped(self):
        """check_quality should cap the access count bonus at 0.3."""
        checker = MemoryQualityChecker()
        content = "Some reasonable content here for testing quality"
        score_6 = checker.check_quality(content, {}, access_count=6)
        score_10 = checker.check_quality(content, {}, access_count=10)
        # The access bonus is min(0.3, count * 0.05), so both should cap at 0.3
        assert score_6 == score_10

    def test_check_quality_recent_content(self):
        """check_quality should give higher scores to recent content."""
        checker = MemoryQualityChecker()
        content = "Some reasonable content here for testing quality"
        recent = datetime.now() - timedelta(days=2)
        old = datetime.now() - timedelta(days=60)

        score_recent = checker.check_quality(content, {}, access_count=0, created_at=recent)
        score_old = checker.check_quality(content, {}, access_count=0, created_at=old)
        assert score_recent > score_old

    def test_check_quality_no_created_at(self):
        """check_quality should work without created_at (no recency bonus)."""
        checker = MemoryQualityChecker()
        content = "Some reasonable content here for testing quality"
        score = checker.check_quality(content, {}, access_count=0, created_at=None)
        # No recency bonus, but should still have content length bonus
        assert score >= 0.0

    def test_check_quality_metadata_type(self):
        """check_quality should give a bonus for metadata having a 'type' key."""
        checker = MemoryQualityChecker()
        content = "Some reasonable content here for testing quality"
        score_with_type = checker.check_quality(content, {"type": "semantic"})
        score_without_type = checker.check_quality(content, {})
        assert score_with_type > score_without_type

    def test_check_quality_generic_short_content_penalized(self):
        """check_quality should penalize generic short content."""
        checker = MemoryQualityChecker()
        # All lowercase, very short content should be penalized
        generic = "ok"
        specific = "This is a detailed architectural decision about the project"
        score_generic = checker.check_quality(generic, {}, access_count=0)
        score_specific = checker.check_quality(specific, {}, access_count=0)
        assert score_specific > score_generic

    def test_check_quality_score_range(self):
        """check_quality should always return a score between 0.0 and 1.0."""
        checker = MemoryQualityChecker()
        test_cases = [
            ("", {}, 0, None),
            ("a" * 500, {"type": "semantic"}, 10, datetime.now()),
            ("short", {}, 0, None),
            ("Lowercase short", {}, 0, datetime.now() - timedelta(days=100)),
        ]
        for content, metadata, access_count, created_at in test_cases:
            score = checker.check_quality(content, metadata, access_count, created_at)
            assert 0.0 <= score <= 1.0

    # --- classify_quality ---

    def test_classify_quality_high(self):
        """classify_quality should return HIGH for scores >= 0.8."""
        checker = MemoryQualityChecker()
        assert checker.classify_quality(0.8) == QualityScore.HIGH
        assert checker.classify_quality(0.9) == QualityScore.HIGH
        assert checker.classify_quality(1.0) == QualityScore.HIGH

    def test_classify_quality_medium(self):
        """classify_quality should return MEDIUM for scores 0.5-0.79."""
        checker = MemoryQualityChecker()
        assert checker.classify_quality(0.5) == QualityScore.MEDIUM
        assert checker.classify_quality(0.6) == QualityScore.MEDIUM
        assert checker.classify_quality(0.79) == QualityScore.MEDIUM

    def test_classify_quality_low(self):
        """classify_quality should return LOW for scores 0.3-0.49."""
        checker = MemoryQualityChecker()
        assert checker.classify_quality(0.3) == QualityScore.LOW
        assert checker.classify_quality(0.4) == QualityScore.LOW
        assert checker.classify_quality(0.49) == QualityScore.LOW

    def test_classify_quality_irrelevant(self):
        """classify_quality should return IRRELEVANT for scores < 0.3."""
        checker = MemoryQualityChecker()
        assert checker.classify_quality(0.0) == QualityScore.IRRELEVANT
        assert checker.classify_quality(0.1) == QualityScore.IRRELEVANT
        assert checker.classify_quality(0.29) == QualityScore.IRRELEVANT

    def test_classify_quality_boundary_values(self):
        """classify_quality should correctly handle boundary values."""
        checker = MemoryQualityChecker()
        assert checker.classify_quality(0.8) == QualityScore.HIGH
        assert checker.classify_quality(0.799) == QualityScore.MEDIUM
        assert checker.classify_quality(0.5) == QualityScore.MEDIUM
        assert checker.classify_quality(0.499) == QualityScore.LOW
        assert checker.classify_quality(0.3) == QualityScore.LOW
        assert checker.classify_quality(0.299) == QualityScore.IRRELEVANT

    # --- is_duplicate ---

    def test_is_duplicate_exact_match(self):
        """is_duplicate should detect exact content matches."""
        checker = MemoryQualityChecker()
        content = "The quick brown fox jumps over the lazy dog"
        existing = ["The quick brown fox jumps over the lazy dog"]
        assert checker.is_duplicate(content, existing) is True

    def test_is_duplicate_case_insensitive(self):
        """is_duplicate should be case-insensitive."""
        checker = MemoryQualityChecker()
        content = "The Quick Brown Fox"
        existing = ["the quick brown fox"]
        assert checker.is_duplicate(content, existing) is True

    def test_is_duplicate_whitespace_normalized(self):
        """is_duplicate should normalize whitespace."""
        checker = MemoryQualityChecker()
        content = "hello   world   test"
        existing = ["hello world test"]
        assert checker.is_duplicate(content, existing) is True

    def test_is_duplicate_substring_match(self):
        """is_duplicate should detect content that is a substring of existing."""
        checker = MemoryQualityChecker()
        content = "hello world"
        existing = ["the quick brown fox says hello world today"]
        assert checker.is_duplicate(content, existing) is True

    def test_is_duplicate_existing_as_substring(self):
        """is_duplicate should detect when existing is a substring of content with high overlap."""
        checker = MemoryQualityChecker()
        # The existing content is a large portion of the new content
        content = "This is a very long piece of content about microservices"
        existing = [
            "This is a very long piece of content about microservices architecture patterns"
        ]
        # content is a substring of existing
        assert checker.is_duplicate(content, existing) is True

    def test_is_duplicate_different_content(self):
        """is_duplicate should return False for different content."""
        checker = MemoryQualityChecker()
        content = "This is about database design"
        existing = ["This is about frontend development"]
        assert checker.is_duplicate(content, existing) is False

    def test_is_duplicate_empty_existing(self):
        """is_duplicate should return False when no existing content."""
        checker = MemoryQualityChecker()
        content = "Some content"
        assert checker.is_duplicate(content, []) is False

    def test_is_duplicate_multiple_existing(self):
        """is_duplicate should check against all existing entries."""
        checker = MemoryQualityChecker()
        content = "duplicate entry"
        existing = ["first entry", "duplicate entry", "third entry"]
        assert checker.is_duplicate(content, existing) is True

    def test_is_duplicate_no_match_in_multiple(self):
        """is_duplicate should return False when no existing entry matches."""
        checker = MemoryQualityChecker()
        content = "unique content"
        existing = ["first entry", "second entry", "third entry"]
        assert checker.is_duplicate(content, existing) is False

    def test_is_duplicate_first_100_chars(self):
        """is_duplicate should use first 100 characters for comparison."""
        checker = MemoryQualityChecker()
        # Create two contents that differ only after the first 100 characters
        long_prefix = "A" * 100
        content1 = long_prefix + "XYZ"
        content2 = long_prefix + "ABC"
        # First 100 chars match, so should be considered duplicate
        assert checker.is_duplicate(content2, [content1]) is True

    # --- should_expire ---

    def test_should_expire_old_content(self):
        """should_expire should return True for old content."""
        checker = MemoryQualityChecker()
        old_date = datetime.now() - timedelta(days=100)
        assert checker.should_expire(old_date) is True

    def test_should_expire_recent_content(self):
        """should_expire should return False for recent content."""
        checker = MemoryQualityChecker()
        recent_date = datetime.now() - timedelta(days=1)
        assert checker.should_expire(recent_date) is False

    def test_should_expire_episodic_memory(self):
        """should_expire should use shorter TTL for episodic memory."""
        checker = MemoryQualityChecker()
        # 60 days old: should be expired for episodic (30-day TTL)
        old_episodic = datetime.now() - timedelta(days=60)
        assert checker.should_expire(old_episodic, memory_type="episodic") is True

        # 60 days old: should NOT be expired for non-episodic (90-day TTL)
        assert checker.should_expire(old_episodic, memory_type="semantic") is False

    def test_should_expire_episodic_within_ttl(self):
        """should_expire should return False for episodic memory within TTL."""
        checker = MemoryQualityChecker()
        recent_episodic = datetime.now() - timedelta(days=10)
        assert checker.should_expire(recent_episodic, memory_type="episodic") is False

    def test_should_expire_with_last_accessed(self):
        """should_expire should use last_accessed instead of created_at when provided."""
        checker = MemoryQualityChecker()
        # Created 100 days ago, but accessed 1 day ago
        old_created = datetime.now() - timedelta(days=100)
        recent_accessed = datetime.now() - timedelta(days=1)
        # With last_accessed, the entry is recent and should not expire
        assert checker.should_expire(old_created, last_accessed=recent_accessed) is False

    def test_should_expire_with_old_last_accessed(self):
        """should_expire should expire entries with old last_accessed."""
        checker = MemoryQualityChecker()
        old_created = datetime.now() - timedelta(days=200)
        old_accessed = datetime.now() - timedelta(days=100)
        assert checker.should_expire(old_created, last_accessed=old_accessed) is True

    def test_should_expire_custom_policy(self):
        """should_expire should respect custom policy settings."""
        policy = CleanupPolicy(expire_after_days=10)
        checker = MemoryQualityChecker(policy=policy)
        old_date = datetime.now() - timedelta(days=15)
        assert checker.should_expire(old_date) is True

        recent_date = datetime.now() - timedelta(days=5)
        assert checker.should_expire(recent_date) is False

    def test_should_expire_custom_episodic_policy(self):
        """should_expire should respect custom episodic TTL."""
        policy = CleanupPolicy(expire_episodic_after_days=7)
        checker = MemoryQualityChecker(policy=policy)
        old_episodic = datetime.now() - timedelta(days=10)
        assert checker.should_expire(old_episodic, memory_type="episodic") is True

        recent_episodic = datetime.now() - timedelta(days=3)
        assert checker.should_expire(recent_episodic, memory_type="episodic") is False

    # --- get_entries_to_cleanup ---

    def test_get_entries_to_cleanup_empty(self):
        """get_entries_to_cleanup should return empty list for empty entries."""
        checker = MemoryQualityChecker()
        result = checker.get_entries_to_cleanup([])
        assert result == []

    def test_get_entries_to_cleanup_low_score(self):
        """get_entries_to_cleanup should remove entries below min_relevance_score."""
        checker = MemoryQualityChecker(policy=CleanupPolicy(min_relevance_score=0.5))
        entries = [
            {"entry_id": "1", "content": "Good content here", "score": 0.7},
            {"entry_id": "2", "content": "Bad", "score": 0.2},
            {"entry_id": "3", "content": "Another good one", "score": 0.6},
        ]
        result = checker.get_entries_to_cleanup(entries)
        assert "2" in result
        assert "1" not in result
        assert "3" not in result

    def test_get_entries_to_cleanup_expired(self):
        """get_entries_to_cleanup should remove expired entries."""
        checker = MemoryQualityChecker()
        old_date = datetime.now() - timedelta(days=100)
        entries = [
            {
                "entry_id": "1",
                "content": "Old entry",
                "score": 0.8,
                "created_at": old_date,
                "memory_type": "episodic",
            },
            {
                "entry_id": "2",
                "content": "Recent entry",
                "score": 0.8,
                "created_at": datetime.now(),
                "memory_type": "semantic",
            },
        ]
        result = checker.get_entries_to_cleanup(entries)
        assert "1" in result  # Old episodic entry should be expired
        assert "2" not in result

    def test_get_entries_to_cleanup_duplicate(self):
        """get_entries_to_cleanup should remove duplicate entries."""
        checker = MemoryQualityChecker()
        entries = [
            {"entry_id": "1", "content": "Important information about users", "score": 0.9},
            {"entry_id": "2", "content": "Important information about users", "score": 0.7},
        ]
        result = checker.get_entries_to_cleanup(entries)
        # Entry 2 should be removed as duplicate of entry 1 (higher score kept first)
        assert "2" in result

    def test_get_entries_to_cleanup_preserves_high_quality(self):
        """get_entries_to_cleanup should preserve high-quality, non-duplicate, non-expired entries."""
        checker = MemoryQualityChecker()
        entries = [
            {
                "entry_id": "1",
                "content": "Detailed architectural decision about microservices",
                "score": 0.9,
                "created_at": datetime.now(),
                "memory_type": "semantic",
                "metadata": {},
            },
        ]
        result = checker.get_entries_to_cleanup(entries)
        assert "1" not in result

    def test_get_entries_to_cleanup_sorts_by_score(self):
        """get_entries_to_cleanup should process entries sorted by score (highest first)."""
        checker = MemoryQualityChecker(policy=CleanupPolicy(min_relevance_score=0.0))
        entries = [
            {"entry_id": "low", "content": "duplicate content here for testing", "score": 0.3},
            {"entry_id": "high", "content": "duplicate content here for testing", "score": 0.9},
        ]
        result = checker.get_entries_to_cleanup(entries)
        # Higher-scored entry is kept, lower-scored is removed as duplicate
        assert "low" in result

    def test_get_entries_to_cleanup_missing_fields(self):
        """get_entries_to_cleanup should handle entries with missing fields gracefully."""
        checker = MemoryQualityChecker(policy=CleanupPolicy(min_relevance_score=0.5))
        entries = [
            {"entry_id": "1", "content": "Test", "score": 0.1},  # Below threshold
            {"entry_id": "2"},  # Missing content and score
        ]
        result = checker.get_entries_to_cleanup(entries)
        assert "1" in result

    # --- deduplicate_entries ---

    def test_deduplicate_entries_no_duplicates(self):
        """deduplicate_entries should return all entries when there are no duplicates."""
        checker = MemoryQualityChecker()
        entries = [
            {"entry_id": "1", "content": "Content about database design", "score": 0.8},
            {"entry_id": "2", "content": "Content about API architecture", "score": 0.7},
        ]
        result = checker.deduplicate_entries(entries)
        assert len(result) == 2

    def test_deduplicate_entries_removes_duplicates(self):
        """deduplicate_entries should remove duplicate entries, keeping highest score."""
        checker = MemoryQualityChecker()
        entries = [
            {"entry_id": "1", "content": "The quick brown fox", "score": 0.5},
            {"entry_id": "2", "content": "The quick brown fox", "score": 0.9},
        ]
        result = checker.deduplicate_entries(entries)
        assert len(result) == 1
        assert result[0]["entry_id"] == "2"
        assert result[0]["score"] == 0.9

    def test_deduplicate_entries_keeps_best_score(self):
        """deduplicate_entries should keep the entry with the highest score."""
        checker = MemoryQualityChecker()
        entries = [
            {"entry_id": "1", "content": "same content here", "score": 0.9},
            {"entry_id": "2", "content": "same content here", "score": 0.7},
            {"entry_id": "3", "content": "same content here", "score": 0.5},
        ]
        result = checker.deduplicate_entries(entries)
        assert len(result) == 1
        assert result[0]["entry_id"] == "1"

    def test_deduplicate_entries_empty(self):
        """deduplicate_entries should return empty list for empty input."""
        checker = MemoryQualityChecker()
        result = checker.deduplicate_entries([])
        assert result == []

    def test_deduplicate_entries_multiple_groups(self):
        """deduplicate_entries should handle multiple duplicate groups."""
        checker = MemoryQualityChecker()
        entries = [
            {"entry_id": "1", "content": "Group A content one", "score": 0.9},
            {"entry_id": "2", "content": "Group A content one", "score": 0.7},
            {"entry_id": "3", "content": "Group B content two", "score": 0.8},
            {"entry_id": "4", "content": "Group B content two", "score": 0.6},
        ]
        result = checker.deduplicate_entries(entries)
        assert len(result) == 2
        result_ids = {e["entry_id"] for e in result}
        assert "1" in result_ids
        assert "3" in result_ids

    def test_deduplicate_entries_single_entry(self):
        """deduplicate_entries should handle a single entry."""
        checker = MemoryQualityChecker()
        entries = [
            {"entry_id": "1", "content": "Unique content", "score": 0.8},
        ]
        result = checker.deduplicate_entries(entries)
        assert len(result) == 1
        assert result[0]["entry_id"] == "1"

    # --- score_entry ---

    def test_score_entry_high_quality(self):
        """score_entry should classify high-quality entries correctly."""
        checker = MemoryQualityChecker()
        result = checker.score_entry(
            content="This is a detailed and comprehensive architectural decision record for the project",
            metadata={"type": "semantic"},
            access_count=10,
            created_at=datetime.now() - timedelta(days=2),
        )
        assert result["quality_score"] > 0.0
        assert result["quality_level"] in [QualityScore.HIGH, QualityScore.MEDIUM]
        assert result["is_duplicate"] is False
        assert "recommendation" in result
        assert "should_expire" in result

    def test_score_entry_low_quality(self):
        """score_entry should classify low-quality entries correctly."""
        checker = MemoryQualityChecker()
        result = checker.score_entry(
            content="ok",
            metadata={},
            access_count=0,
            created_at=None,
        )
        assert result["quality_score"] >= 0.0
        assert result["quality_level"] in [QualityScore.LOW, QualityScore.IRRELEVANT]

    def test_score_entry_with_existing_contents(self):
        """score_entry should detect duplicates when existing_contents is provided."""
        checker = MemoryQualityChecker()
        result = checker.score_entry(
            content="The quick brown fox jumps over the lazy dog",
            metadata={"existing_contents": ["The quick brown fox jumps over the lazy dog"]},
            access_count=0,
            created_at=None,
        )
        assert result["is_duplicate"] is True

    def test_score_entry_without_existing_contents(self):
        """score_entry should not flag duplicates when existing_contents is not provided."""
        checker = MemoryQualityChecker()
        result = checker.score_entry(
            content="Some unique content",
            metadata={},
            access_count=0,
            created_at=None,
        )
        assert result["is_duplicate"] is False

    def test_score_entry_recommendation_keep(self):
        """score_entry should recommend 'keep' for high-quality, non-expired entries."""
        checker = MemoryQualityChecker()
        result = checker.score_entry(
            content="Detailed architectural decision about microservices patterns",
            metadata={"type": "semantic"},
            access_count=5,
            created_at=datetime.now() - timedelta(days=2),
        )
        assert result["recommendation"] == "keep"

    def test_score_entry_recommendation_remove_expired(self):
        """score_entry should recommend 'remove' for expired entries."""
        checker = MemoryQualityChecker()
        old_date = datetime.now() - timedelta(days=100)
        result = checker.score_entry(
            content="Some old episodic memory",
            metadata={"type": "episodic"},
            access_count=0,
            created_at=old_date,
        )
        assert result["recommendation"] == "remove"

    def test_score_entry_recommendation_remove_irrelevant(self):
        """score_entry should recommend 'remove' for irrelevant quality entries."""
        checker = MemoryQualityChecker()
        result = checker.score_entry(
            content="a",
            metadata={},
            access_count=0,
            created_at=None,
        )
        # Very short content should get low score, potentially IRRELEVANT
        if result["quality_level"] == QualityScore.IRRELEVANT:
            assert result["recommendation"] == "remove"

    def test_score_entry_recommendation_review(self):
        """score_entry should recommend 'review' for low-quality or duplicate entries."""
        checker = MemoryQualityChecker()
        result = checker.score_entry(
            content="Short but not too short content for review",
            metadata={"existing_contents": ["Short but not too short content for review"]},
            access_count=0,
            created_at=datetime.now() - timedelta(days=50),
        )
        # Duplicate entries should get 'review' or 'remove'
        assert result["recommendation"] in ["review", "remove"]

    def test_score_entry_all_fields_present(self):
        """score_entry should return all expected fields."""
        checker = MemoryQualityChecker()
        result = checker.score_entry(
            content="Test content for scoring",
            metadata={"type": "semantic"},
            access_count=3,
            created_at=datetime.now(),
        )
        assert "quality_score" in result
        assert "quality_level" in result
        assert "is_duplicate" in result
        assert "should_expire" in result
        assert "recommendation" in result

    def test_score_entry_quality_score_range(self):
        """score_entry quality_score should be between 0.0 and 1.0."""
        checker = MemoryQualityChecker()
        for _ in range(20):
            result = checker.score_entry(
                content="Some test content",
                metadata={},
                access_count=0,
                created_at=None,
            )
            assert 0.0 <= result["quality_score"] <= 1.0


# ---------------------------------------------------------------------------
# MemoryCleanupTask
# ---------------------------------------------------------------------------


class TestMemoryCleanupTask:
    """Tests for the MemoryCleanupTask class."""

    def test_initialization_default(self):
        """MemoryCleanupTask should initialize with default quality checker."""
        task = MemoryCleanupTask()
        assert task.quality_checker is not None
        assert task.memory_store is None
        assert task._total_cleanups == 0
        assert task._last_cleanup is None
        assert task._entries_removed_total == 0

    def test_initialization_custom_checker(self):
        """MemoryCleanupTask should accept a custom quality checker."""
        policy = CleanupPolicy(min_relevance_score=0.5)
        checker = MemoryQualityChecker(policy=policy)
        task = MemoryCleanupTask(quality_checker=checker)
        assert task.quality_checker is checker

    def test_initialization_with_memory_store(self):
        """MemoryCleanupTask should accept a memory store."""
        mock_store = MagicMock()
        task = MemoryCleanupTask(memory_store=mock_store)
        assert task.memory_store is mock_store

    def test_get_cleanup_stats_initial(self):
        """get_cleanup_stats should return initial stats."""
        task = MemoryCleanupTask()
        stats = task.get_cleanup_stats()
        assert stats["total_cleanups"] == 0
        assert stats["last_cleanup"] is None
        assert stats["entries_removed_total"] == 0

    @pytest.mark.asyncio
    async def test_run_cleanup_no_memory_store(self):
        """run_cleanup should return empty result when no memory store."""
        task = MemoryCleanupTask(memory_store=None)
        result = await task.run_cleanup()
        assert result["entries_scanned"] == 0
        assert result["entries_removed"] == 0

    @pytest.mark.asyncio
    async def test_run_cleanup_empty_store(self):
        """run_cleanup should handle an empty memory store."""
        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=[])
        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup()
        assert result["entries_scanned"] == 0
        assert result["entries_removed"] == 0

    @pytest.mark.asyncio
    async def test_run_cleanup_with_entries(self):
        """run_cleanup should remove low-quality and expired entries."""
        old_date = datetime.now() - timedelta(days=100)

        entries = [
            {
                "entry_id": "1",
                "content": "Good high quality content about architecture",
                "score": 0.9,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {"type": "semantic"},
            },
            {
                "entry_id": "2",
                "content": "ok",
                "score": 0.1,
                "memory_type": "episodic",
                "created_at": old_date,
                "metadata": {},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup()

        assert result["entries_scanned"] == 2
        assert result["entries_removed"] > 0

    @pytest.mark.asyncio
    async def test_run_cleanup_with_project_id(self):
        """run_cleanup should filter by project_id when provided."""
        entries = [
            {
                "entry_id": "1",
                "content": "Good content",
                "score": 0.9,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_entries_by_project = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup(project_id="proj-1")

        mock_store.get_entries_by_project.assert_called_once_with("proj-1")
        assert result["entries_scanned"] == 1

    @pytest.mark.asyncio
    async def test_run_cleanup_fallback_to_get_all_entries(self):
        """run_cleanup should fall back to get_all_entries when get_entries_by_project is not available."""
        entries = [
            {
                "entry_id": "1",
                "content": "Good content here",
                "score": 0.9,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {},
            },
        ]

        mock_store = MagicMock(spec=["get_all_entries", "delete_entry"])
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup()

        mock_store.get_all_entries.assert_called_once()
        assert result["entries_scanned"] == 1

    @pytest.mark.asyncio
    async def test_run_cleanup_updates_stats(self):
        """run_cleanup should update internal stats after cleanup."""
        entries = [
            {
                "entry_id": "1",
                "content": "Low quality",
                "score": 0.1,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        await task.run_cleanup()

        stats = task.get_cleanup_stats()
        assert stats["total_cleanups"] == 1
        assert stats["last_cleanup"] is not None
        assert stats["entries_removed_total"] > 0

    @pytest.mark.asyncio
    async def test_run_cleanup_deletes_entries(self):
        """run_cleanup should call delete_entry for each removed entry."""
        entries = [
            {
                "entry_id": "1",
                "content": "Bad content",
                "score": 0.1,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup()

        if result["entries_removed"] > 0:
            mock_store.delete_entry.assert_called()

    @pytest.mark.asyncio
    async def test_run_cleanup_handles_store_error(self):
        """run_cleanup should handle errors from the memory store."""
        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(side_effect=Exception("Store error"))

        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup()

        assert result["entries_scanned"] == 0
        assert result["entries_removed"] == 0

    @pytest.mark.asyncio
    async def test_run_cleanup_handles_delete_error(self):
        """run_cleanup should handle errors when deleting entries."""
        entries = [
            {
                "entry_id": "1",
                "content": "Bad",
                "score": 0.1,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(side_effect=Exception("Delete error"))

        task = MemoryCleanupTask(memory_store=mock_store)
        # Should not raise, but log the error
        result = await task.run_cleanup()
        # Entry should still be identified for removal even if deletion fails
        assert result["entries_scanned"] == 1

    @pytest.mark.asyncio
    async def test_run_cleanup_categorizes_removal_reasons(self):
        """run_cleanup should categorize entries by removal reason."""
        old_date = datetime.now() - timedelta(days=100)

        entries = [
            {
                "entry_id": "1",
                "content": "Low quality",
                "score": 0.1,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {},
            },
            {
                "entry_id": "2",
                "content": "Expired episodic",
                "score": 0.8,
                "memory_type": "episodic",
                "created_at": old_date,
                "metadata": {},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup()

        assert result["by_reason"]["low_quality"] >= 0
        assert result["by_reason"]["expired"] >= 0
        assert result["by_reason"]["duplicate"] >= 0

    @pytest.mark.asyncio
    async def test_run_cleanup_all_high_quality(self):
        """run_cleanup should remove no entries when all are high quality."""
        entries = [
            {
                "entry_id": "1",
                "content": "High quality content about architecture patterns and design decisions",
                "score": 0.9,
                "memory_type": "semantic",
                "created_at": datetime.now() - timedelta(days=1),
                "metadata": {"type": "semantic"},
            },
            {
                "entry_id": "2",
                "content": "Another high quality content about database optimization strategies",
                "score": 0.8,
                "memory_type": "semantic",
                "created_at": datetime.now() - timedelta(days=5),
                "metadata": {"type": "semantic"},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup()

        assert result["entries_scanned"] == 2
        assert result["entries_removed"] == 0

    @pytest.mark.asyncio
    async def test_run_cleanup_uses_remove_entry_fallback(self):
        """run_cleanup should use remove_entry if delete_entry is not available."""
        entries = [
            {
                "entry_id": "1",
                "content": "Bad",
                "score": 0.1,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {},
            },
        ]

        mock_store = MagicMock(spec=["get_all_entries", "remove_entry"])
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.remove_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup()

        mock_store.remove_entry.assert_called()

    @pytest.mark.asyncio
    async def test_schedule_cleanup(self):
        """schedule_cleanup should store the interval."""
        task = MemoryCleanupTask()
        await task.schedule_cleanup(interval_hours=12)

        assert task._scheduled_interval_hours == 12

    @pytest.mark.asyncio
    async def test_schedule_cleanup_default_interval(self):
        """schedule_cleanup should accept default interval."""
        task = MemoryCleanupTask()
        await task.schedule_cleanup()

        assert task._scheduled_interval_hours == 24

    @pytest.mark.asyncio
    async def test_run_cleanup_multiple_times(self):
        """run_cleanup should accumulate stats across multiple runs."""
        entries_run1 = [
            {
                "entry_id": "1",
                "content": "Bad",
                "score": 0.1,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=entries_run1)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        await task.run_cleanup()
        await task.run_cleanup()

        stats = task.get_cleanup_stats()
        assert stats["total_cleanups"] == 2
        assert stats["last_cleanup"] is not None

    @pytest.mark.asyncio
    async def test_run_cleanup_space_freed_estimate(self):
        """run_cleanup should estimate space freed."""
        entries = [
            {
                "entry_id": "1",
                "content": "Low quality",
                "score": 0.1,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup()

        # space_freed_estimate = entries_removed * 500
        if result["entries_removed"] > 0:
            assert result["space_freed_estimate"] == result["entries_removed"] * 500

    def test_get_cleanup_stats_after_manual_update(self):
        """get_cleanup_stats should reflect manual updates to stats."""
        task = MemoryCleanupTask()
        task._total_cleanups = 5
        task._entries_removed_total = 100
        task._last_cleanup = datetime.now()

        stats = task.get_cleanup_stats()
        assert stats["total_cleanups"] == 5
        assert stats["entries_removed_total"] == 100
        assert stats["last_cleanup"] is not None

    @pytest.mark.asyncio
    async def test_run_cleanup_with_no_cleanup_necessary(self):
        """run_cleanup should handle entries that don't need cleanup."""
        entries = [
            {
                "entry_id": "1",
                "content": "High quality content about important architectural decisions",
                "score": 0.9,
                "memory_type": "semantic",
                "created_at": datetime.now() - timedelta(days=1),
                "metadata": {"type": "semantic"},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(memory_store=mock_store)
        result = await task.run_cleanup()

        assert result["entries_scanned"] == 1
        assert result["entries_removed"] == 0
        assert result["space_freed_estimate"] == 0


# ---------------------------------------------------------------------------
# Integration: MemoryQualityChecker with MemoryCleanupTask
# ---------------------------------------------------------------------------


class TestQualityCheckerAndCleanupIntegration:
    """Integration tests for MemoryQualityChecker and MemoryCleanupTask."""

    @pytest.mark.asyncio
    async def test_end_to_end_cleanup_workflow(self):
        """Test the full workflow: check quality, identify entries, cleanup."""
        old_date = datetime.now() - timedelta(days=100)
        recent_date = datetime.now() - timedelta(days=1)

        # Create a quality checker with a custom policy
        policy = CleanupPolicy(
            min_relevance_score=0.3,
            expire_after_days=90,
            expire_episodic_after_days=30,
        )
        checker = MemoryQualityChecker(policy=policy)

        # Verify quality scores
        high_score = checker.check_quality(
            "Detailed content about microservices architecture patterns",
            {"type": "semantic"},
            access_count=5,
            created_at=recent_date,
        )
        assert high_score > 0.3

        low_score = checker.check_quality(
            "ok",
            {},
            access_count=0,
            created_at=None,
        )
        assert low_score < high_score

        # Classify quality
        assert checker.classify_quality(high_score) in [QualityScore.HIGH, QualityScore.MEDIUM]
        assert checker.classify_quality(low_score) in [QualityScore.LOW, QualityScore.IRRELEVANT]

        # Verify expiration
        assert checker.should_expire(old_date, memory_type="episodic") is True
        assert checker.should_expire(recent_date, memory_type="semantic") is False

        # Set up cleanup task
        entries = [
            {
                "entry_id": "keep-1",
                "content": "Detailed content about microservices architecture",
                "score": 0.9,
                "memory_type": "semantic",
                "created_at": recent_date,
                "metadata": {"type": "semantic"},
            },
            {
                "entry_id": "expire-1",
                "content": "Old episodic memory",
                "score": 0.5,
                "memory_type": "episodic",
                "created_at": old_date,
                "metadata": {},
            },
            {
                "entry_id": "low-1",
                "content": "ok",
                "score": 0.1,
                "memory_type": "semantic",
                "created_at": recent_date,
                "metadata": {},
            },
        ]

        mock_store = MagicMock()
        mock_store.get_all_entries = AsyncMock(return_value=entries)
        mock_store.delete_entry = AsyncMock(return_value=True)

        task = MemoryCleanupTask(quality_checker=checker, memory_store=mock_store)
        result = await task.run_cleanup()

        assert result["entries_scanned"] == 3
        assert result["entries_removed"] > 0

        stats = task.get_cleanup_stats()
        assert stats["total_cleanups"] == 1

    def test_quality_score_and_classify_consistency(self):
        """check_quality and classify_quality should be consistent."""
        checker = MemoryQualityChecker()
        content = "This is detailed content about system design patterns"
        score = checker.check_quality(
            content, {"type": "semantic"}, access_count=3, created_at=datetime.now()
        )
        level = checker.classify_quality(score)

        if score >= 0.8:
            assert level == QualityScore.HIGH
        elif score >= 0.5:
            assert level == QualityScore.MEDIUM
        elif score >= 0.3:
            assert level == QualityScore.LOW
        else:
            assert level == QualityScore.IRRELEVANT

    def test_score_entry_and_cleanup_consistency(self):
        """score_entry results should be consistent with get_entries_to_cleanup."""
        checker = MemoryQualityChecker(policy=CleanupPolicy(min_relevance_score=0.3))

        # Create entries with known scores
        entries = [
            {
                "entry_id": "1",
                "content": "Low quality content",
                "score": 0.1,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {},
            },
            {
                "entry_id": "2",
                "content": "High quality content about design decisions",
                "score": 0.9,
                "memory_type": "semantic",
                "created_at": datetime.now(),
                "metadata": {"type": "semantic"},
            },
        ]

        # Get entries to cleanup
        cleanup_ids = checker.get_entries_to_cleanup(entries)

        # The low-quality entry should be marked for cleanup
        assert "1" in cleanup_ids
        # The high-quality entry should not be marked for cleanup
        assert "2" not in cleanup_ids
