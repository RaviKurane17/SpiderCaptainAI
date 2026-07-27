"""
Concurrency Utilities
Provides a global ThreadPoolExecutor to prevent excessive thread creation
and reduce OS scheduling overhead.
"""
from concurrent.futures import ThreadPoolExecutor

# A global thread pool with a reasonable max_workers limit.
_global_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="CaptainWorker")

def run_in_background(func, *args, **kwargs):
    """
    Submits a function to be executed in the global thread pool.
    """
    return _global_executor.submit(func, *args, **kwargs)
