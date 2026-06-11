# Elastic MCP Sidecar

## Overview

The Elastic MCP server runs as a sidecar container alongside the orchestrator on Cloud Run.

## Configuration

The sidecar uses the official `elastic/mcp-server-elasticsearch` image with a read-only API key:

```yaml
# Cloud Run service with sidecar
containers:
  - name: orchestrator
    image: gcr.io/PROJECT/argus-orchestrator
    ports:
      - containerPort: 8080
    env:
      - name: MCP_SERVER_URL
        value: http://localhost:3333

  - name: mcp-sidecar
    image: docker.elastic.co/mcp/mcp-server-elasticsearch:latest
    env:
      - name: ELASTICSEARCH_URL
        valueFrom:
          secretKeyRef:
            name: elastic-url
      - name: ELASTICSEARCH_API_KEY
        valueFrom:
          secretKeyRef:
            name: elastic-api-key
    ports:
      - containerPort: 3333
```

## Security

- API key is read-only (`viewer` role on `argus-*` indices only)
- No write, admin, or manage_index permissions
- Key stored in Secret Manager, injected at runtime
- MCP server accessible only on loopback (intra-pod)

## Pinning

Pin the MCP server image to a specific SHA to prevent version drift:

```
docker.elastic.co/mcp/mcp-server-elasticsearch@sha256:XXXXX
```
