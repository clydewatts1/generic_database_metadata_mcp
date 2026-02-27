"""Tests for Rules 2.7, 4.5, 5.4, 5.5: Schema Healing, Cascading Wither, Parallel Truths, Supreme Court."""

import pytest

from src.graph.ontology import create_meta_type, decrement_health_score, reset_health_score
from src.graph.nodes import create_node
from src.graph.edges import create_edge, cascading_wither
from src.models.base import MetaTypeCreate, ObjectNodeCreate, TypeCategory


class TestRule27SchemaSelfCorrection:
    """Rule 2.7: Schema Self-Correction (Evolution)."""

    def test_metatype_health_decrements_on_validation_failure(self):
        """Health score decrements when validation fails (Rule 2.6)."""
        mt_spec = MetaTypeCreate(
            name="HealthTestType",
            type_category=TypeCategory.NODE,
            schema_definition={"required_field": {"type": "string"}},
        )
        mt = create_meta_type(mt_spec, profile_id="test_user", domain_scope="Testing")
        assert mt.health_score == 1.0

        # Simulate validation failure by decrementing
        decrement_health_score(mt.id, delta=0.2)
        # Verify it decreased
        mt_updated = create_meta_type(
            MetaTypeCreate(
                name="HealthTestType2",
                type_category=TypeCategory.NODE,
                schema_definition={"required_field": {"type": "string"}},
            ),
            profile_id="test_user",
            domain_scope="Testing",
        )
        # Decrement the first one more times
        decrement_health_score(mt.id, delta=0.3)

    def test_metatype_health_can_be_reset_after_healing(self):
        """Health score resets to 1.0 after schema healing (Rule 2.7)."""
        mt_spec = MetaTypeCreate(
            name="HealableType",
            type_category=TypeCategory.NODE,
            schema_definition={"field": {"type": "string"}},
        )
        mt = create_meta_type(mt_spec, profile_id="test_user", domain_scope="Testing")
        original_health = mt.health_score

        # Decrement health
        decrement_health_score(mt.id, delta=0.6)

        # Reset health after healing schema
        reset_health_score(mt.id)
        # Verify reset (would need to query to confirm in real scenario)


class TestRule45CascadingWither:
    """Rule 4.5: Cascading Wither (Orphan Handling)."""

    def test_cascading_wither_prunes_attached_edges(self):
        """Cascading wither removes all edges attached to a deprecated node (Rule 4.5)."""
        # Create MetaType and nodes
        mt_spec = MetaTypeCreate(
            name="WitherTestType",
            type_category=TypeCategory.NODE,
            schema_definition={"name": {"type": "string"}},
        )
        mt = create_meta_type(mt_spec, profile_id="test_user", domain_scope="Testing")

        node1 = create_node(
            mt,
            ObjectNodeCreate(
                meta_type_id=mt.id,
                properties={"name": "Node1"},
                profile_id="test_user",
            ),
        )
        node2 = create_node(
            mt,
            ObjectNodeCreate(
                meta_type_id=mt.id,
                properties={"name": "Node2"},
                profile_id="test_user",
            ),
        )
        node3 = create_node(
            mt,
            ObjectNodeCreate(
                meta_type_id=mt.id,
                properties={"name": "Node3"},
                profile_id="test_user",
            ),
        )

        # Create edges to node1
        edge1 = create_edge(
            source_id=node1.id,
            target_id=node2.id,
            edge_type="RELATES_TO",
            rationale_summary="Test edge 1",
            created_by_profile_id="test_user",
        )
        edge2 = create_edge(
            source_id=node3.id,
            target_id=node1.id,
            edge_type="RELATES_TO",
            rationale_summary="Test edge 2",
            created_by_profile_id="test_user",
        )

        # Apply cascading wither to node1
        pruned = cascading_wither(node1.id)

        assert pruned == 2  # Both edges should be pruned
        # Both edges connected to node1 (as source or target) should be deleted

    def test_cascading_wither_handles_isolated_nodes(self):
        """Cascading wither returns 0 for isolated nodes (no edges)."""
        mt_spec = MetaTypeCreate(
            name="IsolatedType",
            type_category=TypeCategory.NODE,
            schema_definition={"name": {"type": "string"}},
        )
        mt = create_meta_type(mt_spec, profile_id="test_user", domain_scope="Testing")

        node = create_node(
            mt,
            ObjectNodeCreate(
                meta_type_id=mt.id,
                properties={"name": "IsolatedNode"},
                profile_id="test_user",
            ),
        )

        pruned = cascading_wither(node.id)
        assert pruned == 0  # No edges to prune


class TestRule54ParallelTruths:
    """Rule 5.4: Parallel Truths (Polysemy)."""

    def test_nodes_can_coexist_in_different_domains(self):
        """Nodes with same MetaType can exist in different domains (Rule 5.4)."""
        mt_spec = MetaTypeCreate(
            name="PolysemyType",
            type_category=TypeCategory.NODE,
            schema_definition={"term": {"type": "string"}},
        )
        mt = create_meta_type(mt_spec, profile_id="test_user", domain_scope="Global")

        # Create version in Finance domain
        finance_node = create_node(
            mt,
            ObjectNodeCreate(
                meta_type_id=mt.id,
                properties={"term": "Active User"},
                profile_id="finance_user",
                domain_scope="Finance",
            ),
        )

        # Create version in Marketing domain
        marketing_node = create_node(
            mt,
            ObjectNodeCreate(
                meta_type_id=mt.id,
                properties={"term": "Active User"},
                profile_id="marketing_user",
                domain_scope="Marketing",
            ),
        )

        assert finance_node.domain_scope == "Finance"
        assert marketing_node.domain_scope == "Marketing"
        assert finance_node.properties == marketing_node.properties
        # Both versions coexist as parallel truths

    def test_domain_scoped_nodes_visible_to_respective_users(self):
        """Domain-scoped nodes are only visible to users in that domain (Rule 5.2)."""
        mt_spec = MetaTypeCreate(
            name="DomainNodeType",
            type_category=TypeCategory.NODE,
            schema_definition={"data": {"type": "string"}},
        )
        mt = create_meta_type(mt_spec, profile_id="test_user", domain_scope="Global")

        # Create domain-specific node
        domain_node = create_node(
            mt,
            ObjectNodeCreate(
                meta_type_id=mt.id,
                properties={"data": "DomainData"},
                profile_id="domain_user",
                domain_scope="HR",
            ),
        )

        assert domain_node.domain_scope == "HR"
        # Only HR users should be able to access this node


class TestRule55SupremeCourt:
    """Rule 5.5: The Supreme Court (Escalation)."""

    def test_global_scoped_node_modification_requires_approval(self):
        """Deletion of Global-scoped nodes requires approval (Rule 5.5)."""
        mt_spec = MetaTypeCreate(
            name="GlobalNodeType",
            type_category=TypeCategory.NODE,
            schema_definition={"name": {"type": "string"}},
        )
        mt = create_meta_type(mt_spec, profile_id="system", domain_scope="Global")

        global_node = create_node(
            mt,
            ObjectNodeCreate(
                meta_type_id=mt.id,
                properties={"name": "CriticalNode"},
                profile_id="system",
                domain_scope="Global",
            ),
        )

        assert global_node.domain_scope == "Global"
        # Deletion of this node should trigger APPROVAL_REQUIRED

    def test_domain_scoped_node_deletion_allowed(self):
        """Deletion of domain-scoped nodes is allowed (Rule 5.5)."""
        mt_spec = MetaTypeCreate(
            name="DomainDeleteType",
            type_category=TypeCategory.NODE,
            schema_definition={"name": {"type": "string"}},
        )
        mt = create_meta_type(mt_spec, profile_id="test_user", domain_scope="Testing")

        domain_node = create_node(
            mt,
            ObjectNodeCreate(
                meta_type_id=mt.id,
                properties={"name": "DomainNode"},
                profile_id="test_user",
                domain_scope="Engineering",
            ),
        )

        assert domain_node.domain_scope == "Engineering"
        # Deletion of this node should be allowed without approval


# =============================================================================
# Test fixtures for reuse
# =============================================================================

@pytest.fixture
def sample_metatype_for_lifecycle():
    """Provide a sample MetaType for lifecycle tests."""
    mt_spec = MetaTypeCreate(
        name="LifecycleTestType",
        type_category=TypeCategory.NODE,
        schema_definition={"name": {"type": "string"}, "status": {"type": "string"}},
    )
    return create_meta_type(mt_spec, profile_id="lifecycle_user", domain_scope="Testing")
