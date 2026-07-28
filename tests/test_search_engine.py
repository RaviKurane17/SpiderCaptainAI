import pytest
import time
import threading
import gc
import psutil
import os
from actions.files.engine import FileSearchEngine
from actions.files.cache import SearchCache

@pytest.fixture
def engine():
    # Use an in-memory cache for testing
    cache = SearchCache(db_path=":memory:")
    # Prevent background indexing
    cache.is_stale = lambda x: False
    engine = FileSearchEngine()
    engine._cache = cache
    # Disable default providers to isolate tests, or mock them
    yield engine
    # Cleanup
    if engine._search_thread and engine._search_thread.is_alive():
        engine._search_cancel_event.set()
        engine._search_thread.join(timeout=1.0)
    engine._monitor.stop()

def test_memory_and_thread_leak(engine):
    """Run 100 rapid searches and cancel them to ensure threads don't leak."""
    process = psutil.Process(os.getpid())
    
    gc.collect()
    start_mem = process.memory_info().rss
    start_threads = threading.active_count()
    
    for i in range(100):
        engine.search_async(query=f"leak_test_{i}", max_results=10)
        time.sleep(0.01) # Simulate rapid typing
        
    # Wait for the queue manager to settle
    engine._search_cancel_event.set()
    if engine._search_thread:
        engine._search_thread.join(timeout=2.0)
        
    gc.collect()
    end_mem = process.memory_info().rss
    end_threads = threading.active_count()
    
    # Assert thread count is stable
    assert end_threads <= start_threads + 2, f"Thread leak detected! Started with {start_threads}, ended with {end_threads}"
    
    # Assert memory growth is minimal (less than 20MB)
    mem_diff = (end_mem - start_mem) / (1024 * 1024)
    assert mem_diff < 20.0, f"Memory leak detected! Grew by {mem_diff:.2f} MB"

def test_long_paths_and_unicode(engine):
    """Test queries with unicode characters."""
    # This just ensures the engine normalizes and doesn't crash
    res = engine.search(query="प्रमाणपत्र 测试 résumé 123", max_results=5)
    assert res is not None
    assert "status" in res

def test_cancellation(engine):
    """Test that a new search cancels the old search."""
    import time
    
    # Provide a slow mock provider
    class SlowProvider:
        name = "Slow"
        is_available = True
        def search(self, query, drive=None, is_dir=None, extension=None, max_results=50, on_partial=None):
            time.sleep(2.0) # Long running scan
            return [{"path": "C:\\fake.txt", "name": "fake.txt", "size": 0, "modified_at": 0, "is_dir": False}]
            
    engine._providers = [SlowProvider()]
    
    # Fire first search
    engine.search_async(query="slow1")
    t1 = engine._search_thread
    assert t1 is not None and t1.is_alive()
    
    # Fire second search immediately
    engine.search_async(query="slow2")
    t2 = engine._search_thread
    
    assert t1 != t2 # Threads must be different
    assert engine._search_cancel_event.is_set() == False # Reset for the new thread
    
    # The old thread should die quickly because we set the cancel event inside search_async
    t1.join(timeout=0.5)
    assert not t1.is_alive(), "Old thread did not cancel!"
    assert t2.is_alive(), "New thread should still be running!"
