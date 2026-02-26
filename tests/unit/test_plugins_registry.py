"""Tests for PluginRegistry in agent-vertical."""
from __future__ import annotations

from abc import ABC, abstractmethod
from unittest.mock import MagicMock, patch

import pytest

from agent_vertical.plugins.registry import (
    PluginAlreadyRegisteredError,
    PluginNotFoundError,
    PluginRegistry,
)


# ---------------------------------------------------------------------------
# Test base class
# ---------------------------------------------------------------------------

class BaseProcessor(ABC):
    @abstractmethod
    def process(self, data: str) -> str: ...


class ConcreteProcessor(BaseProcessor):
    def process(self, data: str) -> str:
        return data.upper()


class AnotherProcessor(BaseProcessor):
    def process(self, data: str) -> str:
        return data.lower()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> PluginRegistry[BaseProcessor]:
    return PluginRegistry(BaseProcessor, "processors")


# ---------------------------------------------------------------------------
# Error classes
# ---------------------------------------------------------------------------

class TestPluginNotFoundError:
    def test_error_message_contains_name(self) -> None:
        err = PluginNotFoundError("missing", "my-registry")
        assert "missing" in str(err)

    def test_is_key_error(self) -> None:
        with pytest.raises(KeyError):
            raise PluginNotFoundError("missing", "my-registry")

    def test_attributes(self) -> None:
        err = PluginNotFoundError("my-plugin", "my-registry")
        assert err.plugin_name == "my-plugin"
        assert err.registry_name == "my-registry"


class TestPluginAlreadyRegisteredError:
    def test_error_message_contains_name(self) -> None:
        err = PluginAlreadyRegisteredError("dup", "my-registry")
        assert "dup" in str(err)

    def test_is_value_error(self) -> None:
        with pytest.raises(ValueError):
            raise PluginAlreadyRegisteredError("dup", "my-registry")

    def test_attributes(self) -> None:
        err = PluginAlreadyRegisteredError("dup", "my-registry")
        assert err.plugin_name == "dup"
        assert err.registry_name == "my-registry"


# ---------------------------------------------------------------------------
# PluginRegistry.register (decorator)
# ---------------------------------------------------------------------------

class TestRegisterDecorator:
    def test_register_adds_plugin(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        @registry.register("concrete")
        class _P(BaseProcessor):
            def process(self, data: str) -> str:
                return data

        assert "concrete" in registry

    def test_register_returns_class_unchanged(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        @registry.register("my-proc")
        class _P(BaseProcessor):
            def process(self, data: str) -> str:
                return data

        instance = _P()
        assert instance.process("hello") == "hello"

    def test_register_duplicate_raises(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        registry.register_class("existing", ConcreteProcessor)
        with pytest.raises(PluginAlreadyRegisteredError):
            @registry.register("existing")
            class _P(BaseProcessor):
                def process(self, data: str) -> str:
                    return data

    def test_register_non_subclass_raises_type_error(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        with pytest.raises(TypeError):
            @registry.register("not-a-subclass")
            class _NotAProcessor:
                pass


# ---------------------------------------------------------------------------
# PluginRegistry.register_class
# ---------------------------------------------------------------------------

class TestRegisterClass:
    def test_register_class_directly(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        registry.register_class("concrete", ConcreteProcessor)
        assert "concrete" in registry

    def test_register_class_duplicate_raises(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        registry.register_class("p1", ConcreteProcessor)
        with pytest.raises(PluginAlreadyRegisteredError):
            registry.register_class("p1", AnotherProcessor)

    def test_register_class_non_subclass_raises(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        class _NotProcessor:
            pass
        with pytest.raises(TypeError):
            registry.register_class("bad", _NotProcessor)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PluginRegistry.deregister
# ---------------------------------------------------------------------------

class TestDeregister:
    def test_deregister_existing(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        registry.register_class("p1", ConcreteProcessor)
        registry.deregister("p1")
        assert "p1" not in registry

    def test_deregister_nonexistent_raises(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        with pytest.raises(PluginNotFoundError):
            registry.deregister("nonexistent")


# ---------------------------------------------------------------------------
# PluginRegistry.get
# ---------------------------------------------------------------------------

class TestGet:
    def test_get_registered_plugin(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        registry.register_class("concrete", ConcreteProcessor)
        cls = registry.get("concrete")
        assert cls is ConcreteProcessor

    def test_get_returns_class_not_instance(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        registry.register_class("concrete", ConcreteProcessor)
        cls = registry.get("concrete")
        assert isinstance(cls, type)

    def test_get_missing_raises(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        with pytest.raises(PluginNotFoundError):
            registry.get("nonexistent")


# ---------------------------------------------------------------------------
# PluginRegistry.list_plugins
# ---------------------------------------------------------------------------

class TestListPlugins:
    def test_list_empty(self, registry: PluginRegistry[BaseProcessor]) -> None:
        assert registry.list_plugins() == []

    def test_list_sorted(self, registry: PluginRegistry[BaseProcessor]) -> None:
        registry.register_class("z-proc", ConcreteProcessor)
        registry.register_class("a-proc", AnotherProcessor)
        names = registry.list_plugins()
        assert names == ["a-proc", "z-proc"]

    def test_list_after_deregister(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        registry.register_class("p1", ConcreteProcessor)
        registry.register_class("p2", AnotherProcessor)
        registry.deregister("p1")
        assert "p1" not in registry.list_plugins()


# ---------------------------------------------------------------------------
# PluginRegistry magic methods
# ---------------------------------------------------------------------------

class TestMagicMethods:
    def test_contains_true(self, registry: PluginRegistry[BaseProcessor]) -> None:
        registry.register_class("p1", ConcreteProcessor)
        assert "p1" in registry

    def test_contains_false(self, registry: PluginRegistry[BaseProcessor]) -> None:
        assert "nonexistent" not in registry

    def test_len_empty(self, registry: PluginRegistry[BaseProcessor]) -> None:
        assert len(registry) == 0

    def test_len_after_register(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        registry.register_class("p1", ConcreteProcessor)
        registry.register_class("p2", AnotherProcessor)
        assert len(registry) == 2

    def test_repr_contains_registry_name(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        assert "processors" in repr(registry)

    def test_repr_contains_base_class_name(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        assert "BaseProcessor" in repr(registry)


# ---------------------------------------------------------------------------
# PluginRegistry.load_entrypoints
# ---------------------------------------------------------------------------

class TestLoadEntrypoints:
    def test_load_entrypoints_no_eps(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        with patch("importlib.metadata.entry_points", return_value=[]):
            registry.load_entrypoints("test.group")
        assert len(registry) == 0

    def test_load_entrypoints_registers_valid_plugin(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        ep = MagicMock()
        ep.name = "ep-proc"
        ep.load.return_value = ConcreteProcessor
        with patch("importlib.metadata.entry_points", return_value=[ep]):
            registry.load_entrypoints("test.group")
        assert "ep-proc" in registry

    def test_load_entrypoints_skips_already_registered(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        registry.register_class("ep-proc", ConcreteProcessor)
        ep = MagicMock()
        ep.name = "ep-proc"
        ep.load.return_value = ConcreteProcessor
        with patch("importlib.metadata.entry_points", return_value=[ep]):
            registry.load_entrypoints("test.group")
        # Should still be registered, no error
        assert "ep-proc" in registry

    def test_load_entrypoints_handles_load_exception(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        ep = MagicMock()
        ep.name = "broken-ep"
        ep.load.side_effect = ImportError("module not found")
        with patch("importlib.metadata.entry_points", return_value=[ep]):
            # Should not raise
            registry.load_entrypoints("test.group")
        assert "broken-ep" not in registry

    def test_load_entrypoints_skips_invalid_type(
        self, registry: PluginRegistry[BaseProcessor]
    ) -> None:
        class _NotProcessor:
            pass
        ep = MagicMock()
        ep.name = "bad-ep"
        ep.load.return_value = _NotProcessor
        with patch("importlib.metadata.entry_points", return_value=[ep]):
            registry.load_entrypoints("test.group")
        assert "bad-ep" not in registry
