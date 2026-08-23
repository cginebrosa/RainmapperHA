## Codebase Memory MCP

**MANDATORY: use Codebase Memory MCP graph tools FIRST — before reading files or making code changes.**

This rule applies to every request involving this codebase.

Always call `list_projects` first when you do not already know the project name, then use the `display_name` or exact `name` returned by that tool.

```json
// Step 0 — discover project names
mcp_codebase-memo_list_projects()

// Step 1 — use the project identifier returned above
mcp_codebase-memo_get_architecture({ "project": "<display_name>" })
```

### Workflow

1. Call `list_projects` to discover the correct project name.
2. Call `get_architecture(project)` to understand the codebase structure.
3. Use `search_graph` to find relevant symbols, `trace_call_path` for call chains.
4. Use `get_code_snippet` to read specific function implementations.
5. Only use `read_file` when you need exact raw content to edit a specific line.

### Available Tools (14 MCP tools)

**Indexing:**
- `index_repository(repo_path)` — Index a repository into the knowledge graph
- `list_projects` — List all indexed projects with node/edge counts
- `delete_project(project)` — Remove a project and all its graph data
- `index_status(project)` — Check indexing status

**Querying:**
- `search_graph(name_pattern, name_scope, label, file_pattern, exclude_file_pattern)` — Structured search by label, name/qualified_name, include/exclude file globs
- `trace_call_path(function_name, direction, depth)` — BFS call chain traversal
- `detect_changes(project)` — Map git diff to affected symbols + risk
- `query_graph(query)` — Execute Cypher-like graph queries (read-only)
- `get_graph_schema(project)` — Node/edge counts, relationship patterns
- `get_code_snippet(qualified_name)` — Read source code for a function
- `get_architecture(project)` — Codebase overview: languages, packages, routes, hotspots
- `search_code(pattern, project)` — Grep-like text search within indexed files
- `manage_adr(action)` — CRUD for Architecture Decision Records
- `ingest_traces(traces)` — Ingest runtime traces to validate HTTP edges

## Supervisión de releases HA

Antes de construir o publicar una imagen HA, leer y seguir `docs/release-flow.md`.
Durante `build-push-ha-image.sh`, consultar la misma sesión cada 20-30 segundos,
informar al usuario al menos una vez por minuto y no lanzar builds duplicados. Si
el cliente local no termina después de subir las capas, no cancelarlo hasta
verificar en GHCR los tags de versión y `latest`, el mismo digest y los manifests
`linux/amd64` y `linux/arm64`.

## Validación proporcional

Ejecutar la comprobación mínima suficiente para el riesgo real del cambio.
Cambios solo documentales requieren revisar el diff y `git diff --check`;
código acotado requiere pruebas dirigidas; cambios transversales, de empaquetado
o una release requieren la suite pertinente y, cuando corresponda, el smoke
completo. No repetir el smoke tras commit/push, documentación o bumps mecánicos
si no cambió código ni ningún artefacto ejecutable desde la validación anterior.
