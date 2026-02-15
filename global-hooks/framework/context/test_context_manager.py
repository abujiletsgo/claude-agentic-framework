#!/usr/bin/env python3
"""
Test suite for auto_context_manager.py

Tests the rolling context compression system.
"""

import json
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent))

def test_segment_extraction():
    """Test extracting conversation segments"""
    from auto_context_manager import extract_segments, identify_cold_segments

    # Mock conversation with clear task boundaries
    messages = [
        {"role": "user", "content": "Implement OAuth2 authentication"},
        {"role": "assistant", "content": "I'll implement OAuth2. TaskCreate subject: Implement OAuth2"},
        {"role": "assistant", "content": "...implementing..."},
        {"role": "assistant", "content": "TaskUpdate status: completed. OAuth2 done ✅"},
        {"role": "user", "content": "Now add user profiles"},
        {"role": "assistant", "content": "TaskCreate subject: Add user profiles"},
        {"role": "assistant", "content": "...working on profiles..."},
    ]

    segments = extract_segments(messages)

    assert len(segments) >= 1, f"Expected at least 1 segment, got {len(segments)}"

    # First segment should be OAuth2
    first_seg = segments[0]
    assert "oauth" in str(first_seg["topic"]).lower() or first_seg["completed"], \
        f"First segment should be OAuth2 task: {first_seg}"

    print("✅ test_segment_extraction passed")

def test_cold_detection():
    """Test cold segment detection"""
    from auto_context_manager import identify_cold_segments

    # Segment completed 25 turns ago
    segments = [
        {
            "topic": "Old completed task",
            "last_mentioned_turn": 10,
            "completed": True,
            "messages": [{"content": f"msg {i}"} for i in range(10)]
        },
        {
            "topic": "Recent task",
            "last_mentioned_turn": 33,
            "completed": True,
            "messages": [{"content": f"msg {i}"} for i in range(10)]
        }
    ]

    current_turn = 35

    cold = identify_cold_segments(segments, current_turn)

    # First segment should be cold (35 - 10 = 25 turns)
    # Second segment should NOT be cold (35 - 33 = 2 turns)
    assert len(cold) == 1, f"Expected 1 cold segment, got {len(cold)}"
    assert cold[0]["topic"] == "Old completed task", f"Wrong segment detected as cold: {cold[0]}"

    print("✅ test_cold_detection passed")

def test_queue_operations():
    """Test queue save/load"""
    from auto_context_manager import queue_segments_for_compression, load_queue
    import auto_context_manager as acm

    # Use temp directory for queue
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_queue = Path(tmpdir) / "test_pending.json"

        # Monkey patch get_context_queue_path
        original_get_queue = acm.get_context_queue_path
        acm.get_context_queue_path = lambda: temp_queue

        try:
            # Queue some segments
            segments = [
                {
                    "topic": "Test task 1",
                    "start_turn": 10,
                    "end_turn": 20,
                    "messages": [{"content": "test"}] * 10,
                    "turns_since_mention": 25
                },
                {
                    "topic": "Test task 2",
                    "start_turn": 25,
                    "end_turn": 35,
                    "messages": [{"content": "test"}] * 8,
                    "turns_since_mention": 30
                }
            ]

            queued = queue_segments_for_compression(segments, current_turn=50)

            assert queued == 2, f"Expected 2 segments queued, got {queued}"

            # Load and verify
            queue = load_queue()
            assert len(queue["pending"]) == 2, f"Expected 2 pending, got {len(queue['pending'])}"
            assert queue["last_check_turn"] == 50, f"Expected last_check_turn=50, got {queue['last_check_turn']}"

            print("✅ test_queue_operations passed")

        finally:
            # Restore original function
            acm.get_context_queue_path = original_get_queue

def test_compression_helper():
    """Test compress_segments.py helper"""
    import compress_segments as cs

    with tempfile.TemporaryDirectory() as tmpdir:
        # Monkey patch storage paths
        original_get_l2 = cs.get_l2_storage_dir
        temp_l2 = Path(tmpdir) / "l2_storage"
        temp_l2.mkdir()
        cs.get_l2_storage_dir = lambda: temp_l2

        try:
            # Save a compressed segment
            storage_path = cs.save_compressed_segment(
                segment_id="test_seg_1",
                topic="Test OAuth2 implementation",
                compressed_content="Implemented OAuth2 with JWT tokens...",
                key_decisions=["Used JWT", "1-hour expiry"],
                key_files=["src/auth/oauth2.ts"],
                original_tokens=2400,
                compressed_tokens=350,
                metadata={"start_turn": 10, "end_turn": 30}
            )

            # Verify file exists
            assert Path(storage_path).exists(), f"Storage file not created: {storage_path}"

            # Load and verify
            with open(storage_path, 'r') as f:
                data = json.load(f)

            assert data["segment_id"] == "test_seg_1"
            assert data["topic"] == "Test OAuth2 implementation"
            assert data["original_tokens"] == 2400
            assert data["compressed_tokens"] == 350
            assert data["compression_ratio"] == 6.9  # 2400 / 350 ≈ 6.9
            assert len(data["key_decisions"]) == 2
            assert len(data["key_files"]) == 1

            print("✅ test_compression_helper passed")

        finally:
            cs.get_l2_storage_dir = original_get_l2

def run_all_tests():
    """Run all tests"""
    print("\n🧪 Running Context Manager Tests...\n")

    tests = [
        test_segment_extraction,
        test_cold_detection,
        test_queue_operations,
        test_compression_helper
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__} error: {e}")
            failed += 1

    print(f"\n📊 Results: {passed} passed, {failed} failed")

    return failed == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
