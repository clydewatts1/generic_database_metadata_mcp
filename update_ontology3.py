with open("src/graph/ontology.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('id: ,', 'id: ,')
text = text.replace('name: ,', 'name: ,')
text = text.replace('type_category: ,', 'type_category: ,')
text = text.replace('schema_definition: ,', 'schema_definition: ,')
text = text.replace('health_score: ,', 'health_score: ,')
text = text.replace('version: ,', 'version: ,')
text = text.replace('domain_scope: ,', 'domain_scope: ,')
text = text.replace('created_by_profile_id: ,', 'created_by_profile_id: ,')
text = text.replace('relationship_class: ,', 'relationship_class: ,')
text = text.replace('created_at: ,', 'created_at: ,')
text = text.replace('created_by_prompt_hash: ,', 'created_by_prompt_hash: ,')
text = text.replace('rationale_summary: ', 'rationale_summary: ')

with open("src/graph/ontology.py", "w", encoding="utf-8") as f:
    f.write(text)
