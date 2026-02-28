import pytest
from pydantic import ValidationError
from src.graph.schema import generate_pydantic_model, validate_node_data
from src.models.base import MetaType, TypeCategory
from datetime import datetime, timezone

@pytest.fixture
def sample_meta_type():
    return MetaType(
        id="meta-table-123",
        name="Table",
        type_category=TypeCategory.NODE,
        schema_definition={
            "table_name": "string",
            "row_count": "integer",
            "is_active": "boolean"
        },
        health_score=1.0,
        version=1,
        domain_scope="Global",
        created_by_profile_id="SYSTEM",
        relationship_class="NONE",
        created_by_prompt_hash="xyz",
        created_at=datetime.now(timezone.utc),
        rationale_summary=""
    )

def test_generate_pydantic_model(sample_meta_type):
    DynamicModel = generate_pydantic_model(sample_meta_type)
    
    # Valid data
    valid_data = {
        "table_name": "users",
        "row_count": 100,
        "is_active": True
    }
    instance = DynamicModel(**valid_data)
    assert instance.table_name == "users"
    assert instance.row_count == 100
    assert instance.is_active is True
    
    # Invalid data should raise ValidationError
    with pytest.raises(ValidationError):
        DynamicModel(table_name="users", row_count="not-an-int", is_active=True)

def test_validate_node_data(sample_meta_type):
    valid_data = {
        "table_name": "users",
        "row_count": 100,
        "is_active": True
    }
    # Should not raise exception
    validated = validate_node_data(sample_meta_type, valid_data)
    assert validated["table_name"] == "users"
    
    invalid_data = {
        "table_name": "users",
        "row_count": "bad",
        "is_active": True
    }
    with pytest.raises(ValidationError):
        validate_node_data(sample_meta_type, invalid_data)
