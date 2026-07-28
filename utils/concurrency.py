"""
Concurrency Utilities
Provides adaptive ThreadPoolExecutors separated by workload type to prevent 
heavy IO operations from starving fast UI/System tasks.
"""
import os
from concurrent.futures import ThreadPoolExecutor

# Adaptive worker sizing based on CPU cores
# Use at least 4 workers, up to 16, scaled by 2x CPU cores.
def _get_worker_count():
    cores = os.cpu_count() or 4
    return min(16, max(4, cores * 2))

WORKER_COUNT = _get_worker_count()

# Fast Pool: For extremely quick, non-blocking tasks (Open App, Volume, Settings)
fast_pool = ThreadPoolExecutor(max_workers=WORKER_COUNT, thread_name_prefix="FastPool")

# IO Pool: For heavy disk operations (File Search, Disk Scan, SQLite, OCR)
io_pool = ThreadPoolExecutor(max_workers=WORKER_COUNT, thread_name_prefix="IOPool")

# Network Pool: For API/Network bound tasks (Gemini, Firebase, Web Search)
network_pool = ThreadPoolExecutor(max_workers=WORKER_COUNT, thread_name_prefix="NetPool")

def run_in_background(func, *args, pool=fast_pool, **kwargs):
    """
    Submits a function to be executed in the specified thread pool.
    Defaults to the Fast Pool.
    """
    return pool.submit(func, *args, **kwargs)

def get_fast_pool():
    return fast_pool

def get_io_pool():
    return io_pool

def get_network_pool():
    return network_pool
