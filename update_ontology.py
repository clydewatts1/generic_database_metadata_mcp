with open("src/graph/ontology.py", "r", encoding="utf-8") as f:
    text = f.read()

import re

# Update _row_to_meta_type
text = re.sub(
    r'schema_definition=json\.loads\(props\["schema_definition"\]\),',
    'schema_definition=json.loads(props["schema_definition"]),\n        relationship_class=props.get("relationship_class", "NONE"),\n        created_by_prompt_hash=props.get("created_by_prompt_hash", "SYSTEM_GENERATED"),\n        rationale_summary=props.get("rationale_summary", ""),',
    text
)

# Replace create_meta_type function entirely
old_func = """def create_meta_type(
    data: MetaTypeCreate,
    profile_id: str = "SYSTEM",
    domain_scope: str = "Global",
) -> MetaType:"""

new_func = """def create_meta_type(
    data: MetaTypeCreate,
    profile_id: str = "SYSTEM",
    domain_scope: str = "Global",
) -> MetaType:
    existing = get_meta_type_by_name(data.name)
    if existing is not None:
        raise ValueError(f"MetaType '{data.name}' already exists (id={existing.id}).")
    from datetime import datetime, timezone
    mt = MetaType(
        name=data.name,
        type_category=data.type_category,
        schema_definition=data.schema_definition,
        domain_scope=domain_scope,
        created_by_profile_id=profile_id,
        relationship_class=data.relationship_class,
        created_by_prompt_hash=data.created_by_prompt_hash,
    )

    query = (
        "CREATE (m:MetaType {"
        "  id: ,"
        "  name: ,"
        "  type_category: ,"
        "  schema_definition: ,"
        "  health_score: ,"
        "  version: ,"
        "  domain_scope: ,"
        "  created_by_profile_id: ,"
        "  relationship_class: ,"
        "  created_at: ,"
        "  created_by_prompt_hash: ,"
        "  rationale_summary: "
        "}) RETURN m"
    )
    params = {
        "id": mt.id,
        "name": mt.name,
        "type_category": mt.type_category.value,
        "schema_definition": json.dumps(mt.schema_definition),
        "health_score": mt.health_score,
        "version": mt.version,
        "domain_scope": domain_scope,
        "created_by_profile_id": profile_id,
        "relationship_class": mt.relationship_class.value,
        "created_at": mt.created_at.isoformat(),
        "created_by_prompt_hash": mt.created_by_prompt_hash,
        "rationale_summary": mt.rationale_summary,
    }
    execute_query(query, params)
    logger.info("MetaType created: %s (%s) by %s in domain %s", mt.name, mt.id, profile_id, domain_scope)
    return mt"""

text = re.sub(r'def create_meta_type\(.*?(?=\n# -+)', new_func, text, flags=re.DOTALL)

with open("src/graph/ontology.py", "w", encoding="utf-8") as f:
    f.write(text)
