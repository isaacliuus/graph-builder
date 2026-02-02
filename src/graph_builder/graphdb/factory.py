"""Factory functions for creating GraphDB instances from settings."""

from graph_builder.pipeline.base import GraphDB


def create_graphdb_from_settings() -> GraphDB | None:
    """Create a GraphDB instance from application settings.

    Returns a connected MemgraphGraphDB if GRAPH_BUILDER_USE_GRAPHDB is enabled,
    otherwise returns None.

    Returns:
        A connected GraphDB instance, or None if not enabled.
    """
    from graph_builder.config.settings import get_settings

    settings = get_settings()
    if not settings.use_graphdb:
        return None

    # pylint: disable=import-outside-toplevel
    from graph_builder.graphdb.memgraph import MemgraphGraphDB

    db = MemgraphGraphDB(
        host=settings.memgraph_host,
        port=settings.memgraph_port,
        username=settings.memgraph_username,
        password=settings.memgraph_password,
        database=settings.memgraph_database,
        encrypted=settings.memgraph_encrypted,
    )
    db.connect()
    return db
