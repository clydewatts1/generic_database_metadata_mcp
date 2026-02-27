"""Tests for Rules 5.1-5.3: User Context Injection, Scoped Visibility, Bound Stigmergy."""

import pytest

from src.graph.ontology import create_meta_type, list_meta_types
from src.graph.nodes import create_node
from src.graph.edges import create_edge
from src.models.base import MetaTypeCreate, ObjectNodeCreate, TypeCategory


class TestDomainScopedMetaTypes:
    """Rule 5.2: MetaTypes respect domain_scope visibility."""

    def test_metatype_created_with_profile_and_domain(self):
        """MetaType stores creator profile_id and domain_scope (Rule 5.1-5.2)."""
        mt_spec = MetaTypeCreate(
            name="DomainTestType",
            type_category=TypeCategory.NODE,
            schema_definition={"id": {"type": "string"}},
        )

        # Create MetaType with specific profile and domain
        mt = create_meta_type(
            mt_spec,
            profile_id="user_alice",
            domain_scope="Finance",
        )

        assert mt.created_by_profile_id == "user_alice"
        assert mt.domain_scope == "Finance"

    def test_metatype_defaults_to_global_scope(self):
        """MetaType defaults to Global scope if not specified (Rule 5.2)."""
        mt_spec = MetaTypeCreate(
            name="DefaultGlobalType",
            type_category=TypeCategory.NODE,
            schema_definition={"id": {"type": "string"}},
        )

        mt = create_meta_type(
            mt_spec,
            profile_id="user_bob",
            # domain_scope not specified, should default to "Global"
        )

        assert mt.domain_scope == "Global"
        assert mt.created_by_profile_id == "user_bob"

    def test_list_metatypes_filters_by_domain(self):
        """list_meta_types returns only types in user's domain + Global (Rule 5.2)."""
        # Create MetaTypes in different domains
        finance_type = create_meta_type(
            MetaTypeCreate(
                name="FinanceEntity",
                type_category=TypeCategory.NODE,
                schema_definition={"id": {"type": "string"}},
            ),
            profile_id="user_finance",
            domain_scope="Finance",
        )

        hr_type = create_meta_type(
            MetaTypeCreate(
                name="HREntity",
                type_category=TypeCategory.NODE,
                schema_definition={"id": {"type": "string"}},
            ),
            profile_id="user_hr",
            domain_scope="HR",
        )

        global_type = create_meta_type(
            MetaTypeCreate(
                name="GlobalEntity",
                type_category=TypeCategory.NODE,
                schema_definition={"id": {"type": "string"}},
            ),
            profile_id="user_system",
            domain_scope="Global",
        )

        # Finance user should see Finance + Global types
        finance_types = list_meta_types(domain_scope="Finance")
        assert len(finance_types) == 2
        finance_names = {mt.name for mt in finance_types}
        assert finance_names == {"FinanceEntity", "GlobalEntity"}

        # HR user should see HR + Global types
        hr_types = list_meta_types(domain_scope="HR")
        assert len(hr_types) == 2
        hr_names = {mt.name for mt in hr_types}
        assert hr_names == {"HREntity", "GlobalEntity"}

        # Global user should see all types
        global_types = list_meta_types(domain_scope="Global")
        assert len(global_types) == 3
        global_names = {mt.name for mt in global_types}
        assert global_names == {"FinanceEntity", "HREntity", "GlobalEntity"}


class TestProfileAttributedNodes:
    """Rule 5.1: ObjectNodes are attributed to creating profile_id."""

    def test_node_stores_profile_id(self, sample_metatype):
        """ObjectNode stores the profile_id of its creator (Rule 5.1)."""
        node = create_node(
            sample_metatype,
            ObjectNodeCreate(
                meta_type_id=sample_metatype.id,
                properties={"name": "TestEntity"},
                profile_id="user_charlie",
                domain_scope="Engineering",
            ),
        )

        assert node.profile_id == "user_charlie"
        assert node.domain_scope == "Engineering"

    def test_nodes_default_to_system_profile(self, sample_metatype):
        """ObjectNode defaults to profile_id='SYSTEM' if not specified (Rule 5.1)."""
        node = create_node(
            sample_metatype,
            ObjectNodeCreate(
                meta_type_id=sample_metatype.id,
                properties={"name": "DefaultNode"},
                # profile_id not specified, should default
            ),
        )

        assert node.profile_id == "SYSTEM"


class TestProfileAttributedEdges:
    """Rule 5.3: Stigmergic Edges are attributed to profile_id."""

    def test_edge_stores_created_by_profile_id(self, sample_nodes):
        """StigmergicEdge stores created_by_profile_id (Rule 5.3)."""
        source, target = sample_nodes

        edge = create_edge(
            source_id=source.id,
            target_id=target.id,
            edge_type="RELATES_TO",
            rationale_summary="Test relationship",
            created_by_profile_id="user_diana",
            domain_scope="Marketing",
        )

        assert edge.created_by_profile_id == "user_diana"
        assert edge.domain_scope == "Marketing"

    def test_edge_defaults_to_system_profile(self, sample_nodes):
        """StigmergicEdge defaults to created_by_profile_id='SYSTEM' (Rule 5.3)."""
        source, target = sample_nodes

        edge = create_edge(
            source_id=source.id,
            target_id=target.id,
            edge_type="RELATES_TO",
            rationale_summary="System edge",
            # created_by_profile_id not specified
        )

        assert edge.created_by_profile_id == "SYSTEM"

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def sample_metatype():
    """Provide a sample MetaType for testing."""
    mt_spec = MetaTypeCreate(
        name="TestEntity",
        type_category=TypeCategory.NODE,
        schema_definition={"name": {"type": "string"}},
    )
    return create_meta_type(mt_spec, profile_id="test_user", domain_scope="Testing")


@pytest.fixture
def sample_nodes(sample_metatype):
    """Provide two sample ObjectNodes for edge testing."""
    node1 = create_node(
        sample_metatype,
        ObjectNodeCreate(
            meta_type_id=sample_metatype.id,
            properties={"name": "Node1"},
            profile_id="test_user",
        ),
    )
    node2 = create_node(
        sample_metatype,
        ObjectNodeCreate(
            meta_type_id=sample_metatype.id,
            properties={"name": "Node2"},
            profile_id="test_user",
        ),
    )
    return node1, node2
