import os
import json
import yaml
import tempfile
import pytest

from src.mcp_server.tools.ingestion import bulk_ingest_seed
from src.mcp_server.tools.ontology import register_meta_type
from src.models.base import TypeCategory, RelationshipClass

def test_yaml_seed_ingest_no_context_bloat(ephemeral_graph):
    # 1. Register a MetaType first so bulk ingest has something to validate against
    res_str = register_meta_type(
        name="TestYamlNode",
        type_category=TypeCategory.NODE.value,
        schema_definition={"type": "object", "properties": {"name": {"type": "string"}}},
        relationship_class=RelationshipClass.NONE.value,
        created_by_prompt_hash="TEST_HASH"
    )
    res = json.loads(res_str)
    assert res.get("status") == "SUCCESS"
    
    # 2. Create a temporary YAML file
    yaml_data = {
        "instances": {
            "TestYamlNode": [
                {"name": "Node A"},
                {"name": "Node B"},
                {"name": "Node C"}
            ]
        }
    }
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".yaml", mode='w') as tmp:
        yaml.dump(yaml_data, tmp)
        tmp_path = tmp.name

    try:
        # 3. Use bulk_ingest_seed tool
        result_str = bulk_ingest_seed(file_path=tmp_path)
        result = json.loads(result_str)
        
        # 4. Assert response is context frugal
        assert result.get("success") is True
        assert result.get("nodes_created") == 3
        # Ensure it doesn't return the full nodes (no context bloat)
        assert "Node A" not in result_str
        assert len(result_str) < 500
    finally:
        os.unlink(tmp_path)
