import logging
import threading
from collections import OrderedDict

from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


class LRUMemorySaver(MemorySaver):
    """MemorySaver with LRU eviction to prevent unbounded memory growth.

    Limits the number of stored thread checkpoints and evicts the least-recently-used
    threads when the limit is exceeded. Conversation history is persisted in PostgreSQL
    via the ConversationsController, so evicted checkpoints only affect LangGraph's
    short-term state (which is rebuilt from conversation history on each request).

    :param max_threads: Maximum number of threads to keep checkpoints for
    """

    def __init__(self, max_threads: int = 500):
        super().__init__()
        self._max_threads = max_threads
        self._thread_order: OrderedDict[str, None] = OrderedDict()
        self._lock = threading.Lock()

    def put(self, config, checkpoint, metadata, new_versions):
        result = super().put(config, checkpoint, metadata, new_versions)
        thread_id = config.get("configurable", {}).get("thread_id")
        if thread_id:
            with self._lock:
                self._thread_order[thread_id] = None
                self._thread_order.move_to_end(thread_id)
                while len(self._thread_order) > self._max_threads:
                    oldest_thread, _ = self._thread_order.popitem(last=False)
                    if hasattr(self, "storage") and oldest_thread in self.storage:
                        del self.storage[oldest_thread]
                        logger.debug(f"Evicted checkpoint for thread: {oldest_thread}")
        return result