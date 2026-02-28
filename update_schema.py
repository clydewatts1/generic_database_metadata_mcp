with open('src/models/base.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace(
    '    schema_definition: dict[str, Any] = Field(\n        ...,\n        description="JSON Schema dict defining the fields, types, and required status.",\n    )',
    '    schema_definition: dict[str, Any] = Field(\n        ...,\n        description="JSON Schema dict defining the fields, types, and required status.",\n    )\n    relationship_class: RelationshipClass = RelationshipClass.NONE\n    created_by_prompt_hash: str = "SYSTEM_GENERATED"'
)

text = text.replace(
    '    version: int = Field(default=1)\n    domain_scope: str',
    '    version: int = Field(default=1)\n    relationship_class: RelationshipClass = RelationshipClass.NONE\n    created_at: datetime = Field(default_factory=_now_utc)\n    created_by_prompt_hash: str = "SYSTEM_GENERATED"\n    rationale_summary: str = ""\n    domain_scope: str'
)

text = text.replace(
    '    output_schema: dict[str, Any] = Field(\n        ..., description="JSON Schema for expected output structure"\n    )\n    profile_id: str = Field(default="SYSTEM")',
    '    output_schema: dict[str, Any] = Field(\n        ..., description="JSON Schema for expected output structure"\n    )\n    profile_id: str = Field(default="SYSTEM")\n    created_by_prompt_hash: str = "SYSTEM_GENERATED"'
)

text = text.replace(
    '    created_at: datetime = Field(default_factory=_now_utc)  # Creation timestamp\n    version: int = Field(default=1)',
    '    created_at: datetime = Field(default_factory=_now_utc)  # Creation timestamp\n    created_by_prompt_hash: str = "SYSTEM_GENERATED"\n    version: int = Field(default=1)'
)

with open('src/models/base.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated base.py")
