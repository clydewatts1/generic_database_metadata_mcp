# **Project Constitution: Stigmergic MCP Metadata Server**

## **1\. Core Identity & Architecture**

* **Purpose:** Build a lightweight, context-frugal Model Context Protocol (MCP) server that mimics Teradata Metadata Services, specifically functioning as a "Glossary Weaver."  
* **Tech Stack:** Python, mcp library (MCP Python SDK - mcp -- Run as SSE not STDIO), and FalkorDBLite for the embedded, lightweight graph database.  
* **Core Paradigm:** The system must be **Stigmergic** (the AI leaves "pheromone traces" and semantic connections in the graph environment for future interactions) and **Context Frugal** (never overwhelm the LLM context window).

## **2\. The Dynamic Pydantic Meta-Ontology**

The FalkorDBLite schema operates on a dynamic meta-model, strictly enforced by a runtime Pydantic registry:

* **Rule 2.1 \- Dynamic Type Registration:** The MCP server must maintain an internal, dynamic registry of Object Types and Edge Types. The AI is permitted to define new types on the fly (e.g., creating a Dashboard type with specific required fields).  
* **Rule 2.2 \- Pydantic Generation (create\_model):** When a new Object Type is defined, the server must use pydantic.create\_model to generate a strict validation schema in memory, and persist the schema definition in the graph (e.g., using a (:MetaType) node) so it survives server restarts.  
* **Rule 2.3 \- Pre-Insertion Validation:** All metadata nodes instantiated by the AI must be validated against their dynamically generated Pydantic model *before* being inserted into FalkorDBLite. If attributes are missing or incorrectly typed, the MCP tool must reject the request and return the validation error to the AI.  
* **Rule 2.4 \- Structural vs. Flow Relationships:** Edge Types must clearly distinguish between structural hierarchies (e.g., Table \[:CONTAINS\] Column) and data lineage/flow (e.g., Table\_A \[:POPULATES\] Table\_B).  
* **Rule 2.5 \- Function Objects (First-Class Transformations):** ETL operations or logic must not be hidden inside edge properties. They must be represented as distinct Function Objects within the graph.  
* **Rule 2.6 \- Stigmergic Schema Health:** Every (:MetaType) definition node possesses a health\_score (defaulting to 1.0). When an instantiation or relationship creation fails Pydantic validation, the system must automatically decrement the health\_score of the offending MetaType.  
* **Rule 2.7 \- Schema Self-Correction (Evolution):** The AI must use diagnostic tools to periodically check for (:MetaType) nodes with low health scores. It possesses the authority to patch, evolve, or relax the constraints of these unhealthy types to heal the meta-model organically.  
* **Rule 2.8 \- The Immune System (Circuit Breaker):** The MCP server must implement a 'Circuit Breaker' mechanism. If an AI agent attempts and fails to instantiate an object or heal a schema more than 3 times in a single session due to Pydantic validation errors, the server must hard-lock that specific action and force an explicit human-in-the-loop intervention prompt.

## **3\. The "Context Frugal" Mandate (Non-Negotiable)**

* **Rule 3.1 \- Bounded Cypher Queries:** No open-ended Cypher queries are allowed. All graph traversals must have a strict depth limit (e.g., \*1..2 hops).  
* **Rule 3.2 \- Semantic Compression:** The MCP server must NEVER return raw JSON graph topologies or raw database dumps to the LLM.  
* **Rule 3.3 \- Pagination:** If a Cypher query returns more than 5 connected nodes, the MCP tool must paginate the results or use an LLM-summarization step before returning the string to the client.  
* **Rule 3.4 \- The Genesis Seed (Cold Start):** For Day-0 ingestion, the MCP server must provide a dedicated bulk\_ingest\_seed tool that bypasses the LLM's context window. The AI is only permitted to pass a file path (e.g., a CSV of Teradata schema dumps) to this tool, allowing the Python server to silently build the initial un-weighted graph in the background without flooding the context.  
* **Rule 3.5 \- Compact Output Serialization (TOON/Compact Protocol):** To strictly minimize token consumption, the MCP server must not return verbose, unoptimized JSON arrays for multi-node responses. It must utilize a token-efficient serialization format (such as Token-Oriented Object Notation \- TOON) that strips redundant keys, uses minimal delimiters, and reduces syntactic noise before passing the payload back to the LLM.

## **4\. The Stigmergic Execution Mandate (Confidence-Weighted Web)**

* **Rule 4.1 \- Organic Edge Creation:** When the AI discovers a mapping between a Business Term and a Technical Node, it creates a Stigmergic Edge with an initial confidence\_score (e.g., 0.5) and a last\_accessed timestamp.  
* **Rule 4.2 \- Pheromone Reinforcement:** Every time an existing Stigmergic Edge is successfully traversed to answer a user's query, the AI/Server must trigger a background update to increment the confidence\_score (capping at 1.0) and update the last\_accessed timestamp.  
* **Rule 4.3 \- Biological Decay & Pruning:** The system must enforce a "decay" mechanism. If an edge's last\_accessed timestamp ages past a specific threshold, its confidence\_score degrades. If the score falls below a minimum threshold (e.g., 0.1), the edge is automatically deleted to prune AI hallucinations.  
* **Rule 4.4 \- Immutable Provenance (Audit Trail):** Every Stigmergic Edge or MetaType modification generated by the AI must include a rationale\_summary attribute and a created\_by\_prompt\_hash. This guarantees a human-readable audit trail explaining the logic behind the AI's structural changes.  
* **Rule 4.5 \- Cascading Wither (Orphan Handling):** If an underlying technical node is flagged as "Deprecated" or "Deleted," the MCP server must inflict an immediate and massive decay penalty on all attached stigmergic edges, severing dead branches to prevent hallucinated routing.

## **5\. The Profile-Aware Scoping Mandate**

* **Rule 5.1 \- User Context Injection:** Every MCP tool invocation must automatically receive the current user's profile\_id and domain\_scope (e.g., Finance, Marketing, Global).  
* **Rule 5.2 \- Scoped Visibility:** The AI is strictly prohibited from returning metadata (nodes) that fall outside the user's defined rule scope. Cypher queries must dynamically inject scope filters (e.g., WHERE node.domain IN $user\_scopes).  
* **Rule 5.3 \- Bound Stigmergy:** When a user's action triggers a pheromone reinforcement (Rule 4.2) or edge creation (Rule 4.1), the system must attribute that stigmergic trace to the user's profile, ensuring cross-domain contamination is minimized.  
* **Rule 5.4 \- Parallel Truths (Polysemy):** If the AI detects conflicting stigmergic connections with high confidence from different domain scopes (e.g., Finance vs. Marketing), it must branch the Business Term into domain-specific nodes (e.g., Active User (Finance)) rather than overwriting or deleting conflicting definitions, allowing parallel truths to co-exist securely.  
* **Rule 5.5 \- The Supreme Court (Escalation):** While the AI can freely create and weave, any attempt to delete an Object Type, drop a MetaType definition, or destructively modify a 'Global' scoped node requires an explicit \[APPROVAL\_REQUIRED\] payload to be sent to the client, acting as a human-in-the-loop Supreme Court for irreversible structural changes.

## **6\. The Testing & Validation Mandate**

* **Rule 6.1 \- Test-Driven Stigmergy:** All stigmergic mechanics (e.g., Biological Decay, Schema Health, Cascading Wither) must have dedicated unit tests. The AI must write tests that explicitly mock time progression (e.g., using freezegun) to prove that confidence scores decay and dead links are pruned as expected.  
* **Rule 6.2 \- Frugality Assertion:** Every read-focused MCP tool must include tests that assert the maximum payload size or node count. Tests must explicitly fail if a query returns raw, uncompressed topologies or exceeds the pagination threshold.  
* **Rule 6.3 \- Ephemeral Sandbox:** All tests must be completely isolated using ephemeral, in-memory instances of FalkorDBLite. The AI is strictly prohibited from writing tests that rely on or mutate an external, persistent graph state.