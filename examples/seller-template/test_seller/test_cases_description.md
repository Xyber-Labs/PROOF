Unit tests:

1) All routers are unit-tested against the real FastAPI routes and schemas.

Happy path:
- Each endpoint is called with a declared payload (as in the OpenAPI/Swagger schema).
- For discrete parameters (literals, booleans) we cover each allowed option.
- MCP tools are covered both as hybrid (REST + MCP) and MCP-only flows.
  - Implemented by:
    - `tests/test_mcp_routes.py::test_get_analysis_returns_text`
    - `tests/test_mcp_routes.py::test_hello_robot_returns_hello`
- For continuous parameters, we pick representative values from different ranges.

Additionally, the basic API routers are covered:
- `/api/health` returns 200 with service metadata.
  - Implemented by: `tests/test_api_routes.py::test_health_endpoint_returns_ok`.
- `/api/admin/logs` returns 200 with a list of logs in the unit/in-process context (no x402).
  - Implemented by: `tests/test_api_routes.py::test_admin_logs_returns_log_entries`.

Hybrid endpoints:
- `/hybrid/execute` accepts ExecutionRequest and returns task_id and buyer_secret.
  - Implemented by: `tests/test_hybrid_routes.py::test_execute_endpoint_validates_request`
- `/hybrid/tasks/{task_id}` requires X-Buyer-Secret header and returns task status.
  - Implemented by: `tests/test_hybrid_routes.py::test_tasks_endpoint_requires_buyer_secret`

Edge Cases:
- When validation is present, we test edge cases:
  - Missing required fields return 422.
  - Invalid task_id format returns 404 or 500.
  - Missing X-Buyer-Secret header returns 422.

Bad Path:

Malformed input:
- Empty body or missing required fields.
- Payloads not in accordance with the schema.
- Missing required headers.

For example:
- `/hybrid/execute` has a test that sends an empty JSON body and asserts a `422` validation error from FastAPI.
  - Implemented by: `tests/test_hybrid_routes.py::test_execute_endpoint_validates_request`.
- `/hybrid/tasks/{task_id}` has tests that check missing X-Buyer-Secret header.
  - Implemented by: `tests/test_hybrid_routes.py::test_tasks_endpoint_requires_buyer_secret`.

2) x402 wrapper unit test:

The x402 wrapper is treated as a first-class public surface:
- It is mounted on a tiny FastAPI app in `tests/middlewares/test_x402_wrapper.py`.
- Pricing is injected via `PaymentOption` fixtures.
- `get_x402_settings` and `FacilitatorClient` are monkey-patched to deterministic stubs so that verification and settlement do not touch external systems.

Happy path:
- free to use endpoints pass easily
- paid endpoints return 402 response
- if request contains VALID x402 payments - verification with facilitator is happening
	- very important! 

In practice:
- Free endpoints bypass the middleware and are covered by router tests.
- Paid endpoints:
  - Return 402 with a valid `x402PaymentRequiredResponse` when the `X-PAYMENT` header is missing or invalid.
  - Accept a valid `X-PAYMENT` header generated using the same logic as `x402HttpxClient`:
    - We first call the endpoint to get the 402 body and its `accepts` list.
    - We construct a real payment header from those requirements.
    - On the second call the middleware verifies the payment via the stub facilitator, allows the request to pass, and attaches an `X-PAYMENT-RESPONSE` header when settlement succeeds.

Bad path:
- what if x - payment header contains no matching information?
Bad-path coverage includes:
- Sending syntactically valid but semantically mismatched payment headers (e.g. wrong network or asset), which results in a `402` response with the error `"No matching payment requirements found"`.

Implemented by:
- `tests/middlewares/test_x402_wrapper.py::test_missing_payment_header_returns_402`
  - No `X-PAYMENT` header → 402 with valid x402 body (`accepts` list, `error` message).
- `tests/middlewares/test_x402_wrapper.py::test_invalid_payment_header_returns_402`
  - Malformed (non-JSON) `X-PAYMENT` header → 402 with `"Invalid payment header format"`.
- `tests/middlewares/test_x402_wrapper.py::test_valid_payment_header_allows_request_and_sets_response_header`
  - Real header created via `x402Client` → 200 response, `X-PAYMENT-RESPONSE` header set, facilitator stub `verify`/`settle` called.
- `tests/middlewares/test_x402_wrapper.py::test_payment_header_with_wrong_network_returns_no_matching`
  - Tampered `network` field → 402 with `"No matching payment requirements found"`.

=================================
Test-cases for E2E tests

Seller Template:

Happy Path:
- All endpoints work if we follow the schema.
- If an endpoint has multiple payment options - we can follow any of them, all work.
- If an endpoint is hybrid - it works both with REST and MCP.

This is enforced by the pytest-based E2E suite under `test_seller/e2e`:

- **REST-only:**
  - `/api/health`:
    - Implemented by: `test_seller/e2e/test_rest_only.py::test_health_endpoint_available`
  - `/api/admin/logs`:
    - 402 without payment:
      - Implemented by: `test_seller/e2e/test_rest_only.py::test_admin_logs_requires_payment`
    - 200 with x402 payment:
      - Implemented by: `test_seller/e2e/test_rest_only.py::test_admin_logs_succeeds_with_x402`

- **Hybrid (REST + MCP context):**
  - `/hybrid/execute` via REST:
    - Implemented by: `test_seller/e2e/test_hybrid.py::test_hybrid_execute_via_rest`
  - `/hybrid/tasks/{task_id}` via REST:
    - Implemented by: `test_seller/e2e/test_hybrid.py::test_hybrid_tasks_via_rest`
  - `/hybrid/execute`:
    - 402 without payment (if payment enabled):
      - Implemented by: `test_seller/e2e/test_hybrid.py::test_hybrid_execute_requires_payment`
    - Successful paid call (when environment is fully wired):
      - Implemented by: `test_seller/e2e/test_hybrid.py::test_hybrid_execute_succeeds_with_x402`

- **MCP-only tools:**
  - `hello_robot`:
    - Implemented by: `test_seller/e2e/test_mcp_only.py::test_mcp_hello_robot_tool`
  - `get_analysis` (priced MCP tool):
    - currently expected to return 402 without payment:
      - Implemented by: `test_seller/e2e/test_mcp_only.py::test_mcp_analysis_tool_requires_payment`

Edge cases for end-to-end tests include:
- Multiple priced options for the same `operation_id`, ensuring the client can successfully pay with any configured asset/network.
- Malformed or missing fields in live requests (wrong parameter names, bad JSON) returning structured error messages from FastAPI or MCP.

Bad-path behaviour includes:
- 402 responses with clear `error` messages for missing or invalid `X-PAYMENT` headers.
- 402 responses with `"No matching payment requirements found"` when the payment header network/asset does not align with the configured pricing.
- 4xx responses from FastAPI for invalid request bodies or query parameters, with helpful `detail` fields describing the validation failure.
