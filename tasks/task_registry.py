"""Task registry — single entry point for discovering tasks."""

from tasks.definitions import TASKS, get_task, list_task_ids

__all__ = ["TASKS", "get_task", "list_task_ids"]
