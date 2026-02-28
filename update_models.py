import re

with open('src/models/base.py', 'r') as f:
    orig = f.read()

# Add RelationshipClass enum
if 'class RelationshipClass' not in orig:
    orig = orig.replace('class TypeCategory(str, Enum):\n    NODE = "NODE"\n    EDGE = "EDGE"\n',
        'class TypeCategory(str, Enum):\n    NODE = "NODE"\n    EDGE = "EDGE"\n\nclass RelationshipClass(str, Enum):\n    STRUCTURAL = "STRUCTURAL"\n    FLOW = "FLOW"\n    NONE = "NONE"\n')

# Updates to MetaTypeCreate
if 'relationship_class: RelationshipClass' not in orig:
    orig = orig.replace('type_category: TypeCategory\n    schema_definition',
        'type_category: TypeCategory\n    schema_definition')

    # Wait, regular expressions are better.
