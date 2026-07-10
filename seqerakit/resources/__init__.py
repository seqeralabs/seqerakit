"""
Resource type parsers and handlers for seqerakit.
"""

from seqerakit.resources import (
    actions,
    compute_envs,
    credentials,
    data_links,
    datasets,
    labels,
    launch,
    members,
    organizations,
    participants,
    pipelines,
    secrets,
    studios,
    teams,
    workspaces,
)
from seqerakit.resources._handlers import handle_generic

# Mapping of resource type names to their parser modules
PARSERS = {
    "actions": actions,
    "compute-envs": compute_envs,
    "credentials": credentials,
    "data-links": data_links,
    "datasets": datasets,
    "labels": labels,
    "launch": launch,
    "members": members,
    "organizations": organizations,
    "participants": participants,
    "pipelines": pipelines,
    "secrets": secrets,
    "studios": studios,
    "teams": teams,
    "workspaces": workspaces,
}

# Mapping of resource type names to their handler modules
# Same as PARSERS since each module has both parse() and handle()
HANDLERS = PARSERS.copy()

__all__ = [
    "actions",
    "compute_envs",
    "credentials",
    "data_links",
    "datasets",
    "labels",
    "launch",
    "members",
    "organizations",
    "participants",
    "pipelines",
    "secrets",
    "studios",
    "teams",
    "workspaces",
    "PARSERS",
    "HANDLERS",
    "handle_generic",
]
