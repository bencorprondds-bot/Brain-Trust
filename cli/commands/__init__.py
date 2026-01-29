"""
Legion CLI Commands

Subcommand modules for the Legion CLI.
"""

from . import status
from . import approve
from . import capabilities
from . import projects
from . import logs
from . import eval_cmd
from . import config

__all__ = [
    "status",
    "approve",
    "capabilities",
    "projects",
    "logs",
    "eval_cmd",
    "config",
]
