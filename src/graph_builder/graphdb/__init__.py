"""Graph database persistence layer with lazy loading for optional dependencies."""

from graph_builder.graphdb.base import GraphDBBase


def __getattr__(name: str):
    """Lazy load MemgraphGraphDB to avoid import errors when neo4j is not installed."""
    if name == "MemgraphGraphDB":
        # pylint: disable=import-outside-toplevel
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        return MemgraphGraphDB
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """List available module attributes including lazy-loaded ones."""
    return ["GraphDBBase", "MemgraphGraphDB"]


__all__ = ["GraphDBBase"]
