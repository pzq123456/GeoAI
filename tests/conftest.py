import pytest

from src.schema import GISDependencies, GeoDataLoader


class Ctx:
    """Minimal stand-in for pydantic_ai.RunContext in tool-level tests.

    Tool functions only read ``ctx.deps``, so duck typing is sufficient and
    keeps these tests independent of agent internals.
    """

    def __init__(self, deps: GISDependencies):
        self.deps = deps


@pytest.fixture
def deps() -> GISDependencies:
    return GISDependencies(loader=GeoDataLoader())


@pytest.fixture
def ctx(deps) -> Ctx:
    return Ctx(deps)
