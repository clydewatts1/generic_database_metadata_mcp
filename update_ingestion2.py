with open("src/mcp_server/tools/ingestion.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('from ...utils.logging import ValidationError'):
        new_lines.append(line)
        new_lines.append('import yaml\n')
        new_lines.append('import os\n')
        continue

    if line.startswith('@mcp.tool()'):
        pass # this is fine
    
    if line.startswith('def bulk_ingest_seed('):
        skip = True
        new_lines.append('@mcp.tool()\n')
        new_lines.append('def bulk_ingest_seed(file_path: str) -> str:\n')
        new_lines.append('    \"\"\"Bulk-ingest initial seed data from a YAML file without overwhelming AI context.\n')
        new_lines.append('    \n')
        new_lines.append('    Returns ONLY a compact summary.\n')
        new_lines.append('    \"\"\"\n')
        new_lines.append('    if not os.path.exists(file_path):\n')
        new_lines.append('        return serialise({"success": False, "nodes_created": 0, "edges_created": 0, "message": f"File not found: {file_path}"})\n')
        new_lines.append('        \n')
        new_lines.append('    try:\n')
        new_lines.append('        with open(file_path, "r", encoding="utf-8") as f:\n')
        new_lines.append('            data = yaml.safe_load(f)\n')
        new_lines.append('    except Exception as e:\n')
        new_lines.append('        return serialise({"success": False, "nodes_created": 0, "edges_created": 0, "message": f"YAML parse error: {e}"})\n')
        new_lines.append('        \n')
        new_lines.append('    nodes_created = 0\n')
        new_lines.append('    edges_created = 0\n')
        new_lines.append('    \n')
        new_lines.append('    if not isinstance(data, dict):\n')
        new_lines.append('        return serialise({"success": False, "nodes_created": 0, "edges_created": 0, "message": "Root of YAML must be an object."})\n')
        new_lines.append('        \n')
        new_lines.append('    for meta_type_name, records in data.get("instances", {}).items():\n')
        new_lines.append('        if not isinstance(records, list):\n')
        new_lines.append('            continue\n')
        new_lines.append('        mt = get_meta_type_by_name(meta_type_name)\n')
        new_lines.append('        if mt is None:\n')
        new_lines.append('            logger.warning(f"MetaType {meta_type_name} not found for bulk ingest.")\n')
        new_lines.append('            continue\n')
        new_lines.append('        summary = bulk_ingest(mt, records, domain_scope="Global", profile_id="SYSTEM")\n')
        new_lines.append('        nodes_created += summary.get("inserted", 0)\n')
        new_lines.append('        \n')
        new_lines.append('    return serialise({\n')
        new_lines.append('        "success": True,\n')
        new_lines.append('        "nodes_created": nodes_created,\n')
        new_lines.append('        "edges_created": edges_created,\n')
        new_lines.append('        "message": f"Ingested {nodes_created} nodes and {edges_created} edges."\n')
        new_lines.append('    })\n')
        continue
        
    if skip:
        # We need to drop everything until the end of the file since bulk_ingest_seed is the last function
        continue
    else:
        # Check if line is the @mcp.tool() right before def bulk_ingest_seed
        if line.startswith('@mcp.tool()') and lines[lines.index(line)+1].startswith('def bulk_ingest_seed'):
            continue
        new_lines.append(line)

with open("src/mcp_server/tools/ingestion.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
