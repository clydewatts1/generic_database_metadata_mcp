with open("src/mcp_server/tools/ingestion.py", "r", encoding="utf-8") as f:
    orig = f.read()

import re

# We will just replace the bulk_ingest_seed function
orig = orig.replace('from ...utils.logging import ValidationError, CircuitBreakerError, NotFoundError, get_logger', 'from ...utils.logging import ValidationError, CircuitBreakerError, NotFoundError, get_logger\nimport yaml\nimport os')

func_re = re.compile(r"@mcp\.tool\(\)\ndef bulk_ingest_seed\(.*?return serialise\(summary\)", re.DOTALL)

new_func = \"\"\"@mcp.tool()
def bulk_ingest_seed(
    file_path: str,
) -> str:
    \"\"\"Bulk-ingest initial seed data from a YAML file without overwhelming AI context.
    
    Returns ONLY a compact summary.
    
    Args:
        file_path: Absolute path to the YAML bulk specification file.
    \"\"\"
    if not os.path.exists(file_path):
        return serialise({"success": False, "nodes_created": 0, "edges_created": 0, "message": f"File not found: {file_path}"})
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except Exception as e:
        return serialise({"success": False, "nodes_created": 0, "edges_created": 0, "message": f"YAML parse error: {e}"})
        
    nodes_created = 0
    edges_created = 0
    
    if not isinstance(data, dict):
        return serialise({"success": False, "nodes_created": 0, "edges_created": 0, "message": "Root of YAML must be an object."})
        
    for meta_type_name, records in data.get("instances", {}).items():
        if not isinstance(records, list):
            continue
        mt = get_meta_type_by_name(meta_type_name)
        if mt is None:
            logger.warning("MetaType %s not found for bulk ingest.", meta_type_name)
            continue
        summary = bulk_ingest(mt, records, domain_scope="Global", profile_id="SYSTEM")
        nodes_created += summary.get("inserted", 0)
        
    return serialise({
        "success": True,
        "nodes_created": nodes_created,
        "edges_created": edges_created,
        "message": f"Ingested {nodes_created} nodes and {edges_created} edges."
    })\"\"\"

orig = func_re.sub(new_func, orig)

with open("src/mcp_server/tools/ingestion.py", "w", encoding="utf-8") as f:
    f.write(orig)
