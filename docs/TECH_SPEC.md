# TECH_SPEC.md
**Project:** container-plus  
**Owner:** AxentX – Product Engineering Lead  
**Status:** Draft (ready for review)  
**Last Updated:** 2026‑06‑16  

---  

## 1. Overview  

**container-plus** is a paid‑upgrade platform that extends popular open‑source container tooling (Docker Engine, Podman, Buildah, and CRI‑O) with enterprise‑grade features and support. It is delivered as a **plug‑in/side‑car service** that can be attached to any existing container runtime without requiring a fork or upstream changes.  

Key value propositions  

| Feature | Description |
|---------|-------------|
| **Secure Image Signing & Policy Enforcement** | Automatic signing of built images, policy‑driven verification at pull time. |
| **Advanced Resource Governance** | Fine‑grained cgroup limits, quota enforcement, and runtime‑level QoS. |
| **Observability Suite** | Centralised metrics, logs, and tracing exported to Prometheus, Loki, and OpenTelemetry collectors. |
| **Enterprise Support API** | Ticket‑creation, SLA tracking, and remote debugging hooks. |
| **License‑Managed Feature Flags** | Feature toggles enforced via a signed license token; enables pay‑per‑feature billing. |

The platform is **runtime‑agnostic**: it discovers the host container runtime via a small discovery daemon and injects its side‑car via the runtime’s native plugin mechanism (Docker Engine API, Podman’s OCI hooks, CRI‑O’s plugin socket, etc.).

---  

## 2. Architecture Overview  

```
+-----------------------------------------------------------+
|                     Container‑Plus Platform               |
|  +-------------------+   +----------------------------+   |
|  | Discovery Daemon  |   | License & Billing Service  |   |
|  +-------------------+   +----------------------------+   |
|           |                         |                     |
|           v                         v                     |
|  +-------------------+   +----------------------------+   |
|  | Side‑car Proxy    |<->| Feature Engine (gRPC)      |   |
|  +-------------------+   +----------------------------+   |
|           |                         |                     |
|           v                         v                     |
|  +-------------------+   +----------------------------+   |
|  | Runtime Hook(s)   |   | Observability Exporter     |   |
|  +-------------------+   +----------------------------+   |
+-----------------------------------------------------------+

External Systems:
- Container Runtime (Docker, Podman, CRI‑O, etc.)
- Registry (Docker Hub, Quay, private registry)
- Monitoring Stack (Prometheus, Loki, Jaeger)
- AxentX Billing & License Service (SaaS)
```

### Core Components  

| Component | Responsibility | Language / Runtime |
|-----------|----------------|--------------------|
| **Discovery Daemon** | Detects installed container runtimes, writes configuration for side‑car injection, watches for runtime restarts. | Go (static binary) |
| **Side‑car Proxy** | Transparent TCP/UNIX‑socket proxy that intercepts runtime API calls, forwards to Feature Engine, and returns enriched responses. | Rust (tokio) |
| **Feature Engine** | Implements paid features (signing, policy, QoS, etc.) exposed via gRPC. Stateless; reads license token from License Service. | Rust (tonic) |
| **License & Billing Service** | Validates signed JWT license tokens, enforces feature flags, reports usage for billing. | Node.js (Express) + PostgreSQL |
| **Observability Exporter** | Emits metrics (Prometheus), logs (Loki), traces (OpenTelemetry) for all internal components and runtime events. | Go (OpenTelemetry SDK) |
| **Runtime Hook(s)** | OCI hook scripts or Docker Engine plugin that launch the Side‑car Proxy on container start/stop. | Bash + Go binary |

---  

## 3. Data Model  

### 3.1 License Token (JWT)

```json
{
  "iss": "axentx.com",
  "sub": "customer-id",
  "exp": 1735689600,
  "features": {
    "image_signing": true,
    "policy_enforcement": true,
    "resource_governance": false,
    "observability": true
  },
  "quota": {
    "signatures_per_month": 5000,
    "policy_checks_per_month": 100000
  },
  "sig": "RSA256..."
}
```

- Signed with AxentX RSA‑2048 private key.  
- Verified by License Service at startup and on each gRPC request.

### 3.2 Policy Object (stored in PostgreSQL)

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `customer_id` | UUID | FK to customer |
| `image_ref` | TEXT | Fully‑qualified image name |
| `allow_unsigned` | BOOLEAN | Override signing requirement |
| `max_layers` | INTEGER | Optional layer count limit |
| `created_at` | TIMESTAMP | Audit |
| `updated_at` | TIMESTAMP | Audit |

### 3.3 Usage Metrics (Prometheus)

- `container_plus_signatures_total{customer_id}` – cumulative signatures.  
- `container_plus_policy_checks_total{customer_id}` – policy evaluations.  
- `container_plus_qos_violations_total{customer_id}` – QoS breach count.

---  

## 4. Key APIs / Interfaces  

### 4.1 gRPC Service – `FeatureEngine`

```proto
service FeatureEngine {
  // Image signing
  rpc SignImage(SignRequest) returns (SignResponse);
  // Policy enforcement
  rpc EvaluatePolicy(PolicyRequest) returns (PolicyResponse);
  // Resource governance
  rpc ApplyQoS(QoSRequest) returns (QoSResponse);
  // Observability ping (heartbeat)
  rpc Ping(Empty) returns (Pong);
}
```

**Message examples**

```proto
message SignRequest {
  string image_ref = 1;          // e.g. "registry.example.com/app:1.2.3"
  bytes  image_tar = 2;          // optional inline tarball (for local builds)
  string license_token = 3;      // JWT
}
message SignResponse {
  string signed_ref = 1;         // e.g. "registry.example.com/app:1.2.3-signed"
  bytes  signature = 2;
}
```

All RPCs are **authenticated** via the `license_token` field; the server validates the JWT before processing.

### 4.2 Runtime Hook – OCI Hook (JSON)

```json
{
  "version": "1.0.0",
  "hook": {
    "path": "/usr/local/bin/container-plus-proxy",
    "args": ["--runtime", "docker"]
  },
  "when": {
    "always": true
  },
  "stages": ["prestart"]
}
```

The hook launches the side‑car proxy with the appropriate runtime flag; the proxy then intercepts the Docker Engine API socket (`/var/run/docker.sock`) or Podman socket.

### 4.3 HTTP Endpoints – License Service  

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/license/validate` | Validate JWT, return feature set. |
| `GET`  | `/api/v1/usage/:customer_id` | Retrieve usage counters for billing. |
| `POST` | `/api/v1/ticket` | Create a support ticket (integrates with internal ticketing). |

All endpoints require **mutual TLS** (client certs issued to AxentX partners).

---  

## 5. Technology Stack  

| Layer | Technology | Reason |
|-------|------------|--------|
| **Discovery & Hooks** | Go (1.22) | Static binary, low footprint, excellent cross‑compilation. |
| **Side‑car Proxy** | Rust (1.73) + Tokio | High‑performance async I/O, safe concurrency for proxying thousands of API calls. |
| **Feature Engine** | Rust + Tonic (gRPC) | Zero‑cost abstractions, native TLS, easy to embed in side‑car. |
| **License Service** | Node.js (20) + Express | Rapid development, good ecosystem for JWT handling. |
| **Database** | PostgreSQL 16 (hosted on AxentX managed cluster) | ACID guarantees for policy storage & usage billing. |
| **Observability** | OpenTelemetry SDK (Go/Rust) → Prometheus, Loki, Jaeger | Vendor‑agnostic telemetry. |
| **Container Runtime Integration** | OCI Hooks, Docker Engine Plugin API, CRI‑O socket | Runtime‑agnostic injection. |
| **Build & CI** | GitHub Actions, Docker Buildx, Cargo, Go Modules | Reproducible multi‑arch builds. |
| **Packaging** | Multi‑arch Docker images (`linux/amd64`, `linux/arm64`) + Helm chart for Kubernetes deployment. | Easy consumption by customers. |

---  

## 6. Dependencies  

| Dependency | Version | License |
|------------|---------|---------|
| `github.com/vllm-project/vllm` | 0.5.1 | Apache‑2.0 |
| `github.com/sglang/sglang` | 0.3.0 | MIT |
| `tokio` | 1.38 | MIT |
| `tonic` | 0.11 | Apache‑2.0 |
| `serde` | 1.0 | MIT/Apache‑2.0 |
| `pgx` (PostgreSQL driver) | 0.7 | MIT |
| `express` | 4.19 | MIT |
| `jsonwebtoken` | 9.0 | MIT |
| `opentelemetry-sdk` | 0.23 | Apache‑2.0 |

All dependencies are vetted for compatibility with AxentX’s security policy (no GPL).

---  

## 7. Deployment Model  

### 7.1 Stand‑alone Host  

```
# Install discovery daemon (systemd service)
curl -L https://releases.axentx.com/container-plus/discovery-linux-amd64 -o /usr/local/bin/container-plus-discovery
chmod +x /usr/local/bin/container-plus-discovery
systemctl enable --now container-plus-discovery.service

# Deploy side‑car as a Docker container
docker run -d \
  --name container-plus-proxy \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /etc/container-plus/license.jwt:/etc/container-plus/license.jwt:ro \
  axentx/container-plus-proxy:latest
```

The discovery daemon writes a systemd unit for the proxy if Docker is detected; otherwise it writes the appropriate OCI hook JSON under `/etc/containers/oci/hooks.d/`.

### 7.2 Kubernetes  

A Helm chart (`axentx/container-plus`) installs:

| Resource | Purpose |
|----------|---------|
| `DaemonSet` | Runs the side‑car on every node, mounts the container runtime socket (`/run/containerd/containerd.sock`). |
| `ConfigMap` | Holds static configuration (policy defaults). |
| `Secret` | Stores the signed license JWT (mounted read‑only). |
| `Service` | Exposes the Feature Engine gRPC endpoint internally (`clusterIP`). |
| `Ingress` | Optional – expose License Service API externally with TLS termination. |

```bash
helm repo add axentx https://charts.axentx.com
helm install container-plus axentx/container-plus \
  --set license.secretName=container-plus-license \
  --set image.tag=v1.2.3
```

### 7.3 High‑Availability  

- **Feature Engine** runs as a stateless gRPC service behind a Kubernetes `Deployment` with replica count ≥ 3.  
- **License Service** uses a PostgreSQL primary‑replica cluster; read‑only endpoints are load‑balanced.  
- **Observability Exporter** pushes to a central Prometheus pushgateway; logs are shipped via Loki’s push API.

---  

## 8. Security Considerations  

| Threat | Mitigation |
|--------|------------|
| **License tampering** | JWT signed with RSA‑2048; verification on every request. |
| **Man‑in‑the‑middle on runtime API** | Side‑car terminates TLS (mutual) when communicating with Feature Engine; Docker socket is only accessible to `container-plus` user group. |
| **Privilege escalation** | Proxy runs as non‑root user; uses Linux capabilities `CAP_NET_BIND_SERVICE` only. |
| **Data leakage** | All telemetry is anonymised; no customer image layers are stored, only hashes. |
| **Supply‑chain** | All binaries built in reproducible CI; signed Docker images (cosign). |

---  

## 9. Testing Strategy  

| Layer | Tool | Scope |
|-------|------|-------|
| Unit | `cargo test`, `go test` | Core logic, JWT validation, policy engine. |
| Integration | `docker-compose` with mock Docker Engine, PostgreSQL, and Prometheus | End‑to‑end request flow (sign → pull). |
| Contract | `grpcurl` + OpenAPI spec for License Service | API compatibility. |
| Load | `k6` scripts simulating 10k concurrent API calls | Performance & QoS enforcement. |
| Security | `gosec`, `cargo-audit`, `trivy` | Static analysis, dependency vulnerabilities. |
| CI | GitHub Actions matrix (linux/amd64, linux/arm64) | Build, test, scan, publish artifacts. |

Test coverage target: **≥ 85 %** for Rust code, **≥ 80 %** for Go components.

---  

## 10. Release & Versioning  

- Semantic Versioning (MAJOR.MINOR.PATCH).  
- **MAJOR** – breaking changes to public API or runtime integration.  
- **MINOR** – new paid features, backward‑compatible enhancements.  
- **PATCH** – bug fixes, security patches.  

Release pipeline:  

1. Tag commit (`vX.Y.Z`).  
2. GitHub Actions builds multi‑arch Docker images, pushes to `axentx/container-plus-proxy`.  
3. Helm chart version bumped automatically.  
4. Changelog generated from PR titles (conventional commits).  

---  

## 11. Open Issues & Future Work  

| Issue | Description | Owner | Target Milestone |
|-------|-------------|-------|------------------|
| **Dynamic Policy Updates** | Implement hot‑reload of policy DB without proxy restart. | Backend Team | v1.3.0 |
| **Multi‑Tenant Isolation** | Separate per‑customer resource quotas in a shared cluster. | Platform Team | v2.0.0 |
| **CLI Front‑end** | Provide `container-plus` CLI for local debugging and token management. | UX Team | v1.4.0 |
| **AI‑Assisted Policy Recommendations** | Leverage vLLM inference to suggest optimal QoS settings based on workload telemetry. | R&D | v2.1.0 |

---  

## 12. Appendices  

### A. Directory Layout (repo root)

```
/cmd
   /discovery          # Go binary
   /proxy              # Rust binary (side‑car)
/src
   /engine             # Rust feature engine
   /license-service    # Node.js Express app
   /observability      # Go exporter
/helm
   /container-plus     # Helm chart
/docker
   Dockerfile.discovery
   Dockerfile.proxy
   Dockerfile.license
/.github
   workflows/ci.yml
README.md
LICENSE
```

### B. Environment Variables  

| Variable | Required | Description |
|----------|----------|-------------|
| `LICENSE_JWT_PATH` | Yes | Path to mounted license token. |
| `POSTGRES_DSN` | Yes (license service) | PostgreSQL connection string. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | No | OTLP collector endpoint. |
| `PROXY_RUNTIME` | Yes (proxy) | `docker` | `podman` | `cri-o`. |
| `FEATURE_ENGINE_ADDR` | Yes (proxy) | gRPC address of Feature Engine (`localhost:50051`). |

---  

*Prepared by the AxentX Product Engineering Lead. All specifications are subject to change based on market validation and compliance reviews.*
