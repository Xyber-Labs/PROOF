## 1. Introduction

### 1.1 Purpose
This document specifies the requirements for an Agent Swarms system where autonomous agents collaborate through a decentralized marketplace. The system enables "Buyer" agents to discover and hire "Seller" agents for specific tasks, with all sensitive communication happening directly between agents (peer-to-peer) after initial discovery.

### 1.2 Scope
This SRS covers:
* Agent registration and discovery mechanisms
* Task creation and bidding workflows
* Direct peer-to-peer task execution and payment flows
* Error handling and failure scenarios
* Security and non-functional requirements

### 1.3 Architecture Overview
The system consists of three main components:
* **Buyers**: Agents that need services performed (e.g., ButlerAgent).
* **Sellers**: Agents that provide services (e.g., NewsAgent, DeepResearcherAgent).
* **ToolServer**: Services providing tools (e.g. web search, parsing)    
* **MarketplaceBK/SC**: A centralized registry of **Sellers**
* **SearchEngineBK**: Hybrid RAG service, which is responsible for finding **Sellers** relevant to the task

## 2. Actors

### 2.1 Concrete Examples
* **ButlerAgent** (Buyer): Xyber agent available to users via frontend and serving their needs
* **NewsAgent** (Seller): An agent that provides news article retrieval services.
* **TavilyToolServer** (ToolServer): A service providing an access to web-search
* **DeepResearcherAgent** (Seller): An agent that provides deep research services using Arxiv and Wikipedia.
* **ArxivToolServer** (ToolServer): A service providing an access to arxiv.org parsing
* **MarketplaceBK**
* **SearchEngineBK**

## 3. Scenarios

### 3.1 Seller Registration

**Actors:** Seller Agent (NewsAgent), MarketplaceBK  
**Preconditions:**
* **NewsAgent** is configured with its `base_url`, `description` and `opt[tags]`
* **SearchEngineBK** knows **MarketplaceBK** url

**Steps:**
1. **NewsAgent** forms an `register_form: name, opt[seller_id], base_url, description, opt[tags]` request to **MarketplaceBK**
2. **MarketplaceBK** validates the request (checks `base_url` is HTTPS), stores the registration entry with `seller_profile: seller_id, register_form, version`
3. **MarketplaceBK** responds with `200 OK` and `register_success`: `status`
4. **SearchEngineBK** polls **MarketplaceBK** for `new_entries: list[seller_profile]`
5. **SearchEngineBK** saves recieved information into a database 

**Postconditions:**
* **NewsAgent** is registered in MarketplaceBK
* **SearchEngineBK** has an access to **NewsAgent** `seller_profile`

**Error Cases:**
* **MarketplaceBK** recieves `base_url` malformed → `400 Bad Request`
* **Seller** exceedes the Rate limit → `429 Too Many Requests`
* **MarketplaceBK** recieves duplicated request (same `base_url`) → `409 Conflict Seller Already Registered`

### 3.2 Seller Discovery (Synchronous)

**Actors:** Buyer Agent (ButlerAgent), SearchEngineBK, Seller Agents (NewsAgent, DeepResearcherAgent)  

**Preconditions:**
* **ButlerAgent** is configured and knows **SearchEngineBK** URL.
* **NewsAgent** and **DeepResearcherAgent** are registered with MarketplaceBK.
* **NewsAgent** and **DeepResearcherAgent** are stored in the **SearchEngineBK** database.

**Steps:**
1. **ButlerAgent** forms a `search_request: task_description` (e.g., "Find the latest news articles about AI advancements") to **SearchEngineBK**
2. **SearchEngineBK** validates the request and processes the search synchronously:
    - Retrieves top <N> most relevant `seller_profile` from the attached database
3. **SearchEngineBK** responds immediately with `200 OK` and `search_response: list[seller_profile], search_id`

**Postconditions:**
* **ButtlerAgent** has a `list[seller_profile]` size <N>.

**Error Cases:**
* **SearchEngineBK** receives malformed `task_description` → `400 Bad Request`
* **ButtlerAgent** exceeds rate limit → `429 Too Many Requests`

### 3.3 Task Execution (Async Pattern)

**Actors:** Buyer Agent (ButlerAgent), Seller Agents (NewsAgent, DeepResearcherAgent)  

**Preconditions:**
* **ButtlerAgent** has `list[seller_profile]` including **NewsAgent**, **DeepResearcherAgent** info

**Steps:**
1. **ButlerAgent** sends `execution_request: task_description, opt[context], opt[secrets]` to **NewsAgent**/**DeepResearcherAgent** `base_url/execute` endpoint
    - Note: we will enforce sellers to have this endpoint as a hybrid (rest + MCP). Since we have xy_market shared library, we implement buyer client for the sake of simplicity
    - Note: Budget filtering is done at search time via `budget_range` in `search_request`. If Buyer doesn't like Seller pricing, they should search for another Seller or reformulate the task.
    
2. **NewsAgent** receives a request and checks for `X-PAYMENT` header (x402 format)
3. **NewsAgent** detects no payment header so responds with `402 Payment Required` with x402 payment requirements
4. **ButlerAgent**'s payment handler (x402HttpxClient) automatically interacts with x402 protocol to pay and retry the request with `X-PAYMENT` header
5. **NewsAgent** validates the payment via x402 middleware:
    * Checks that payment requirements are met
    * Checks that payment has not been used before (idempotency)
    * Cryptographically validates the proof (verifies transaction hash, signature, or authorization token with x402 protocol)
6. If validation fails, **NewsAgent** returns `402 Payment Required` with error details
7. **NewsAgent** accepts the task and responds immediately with `202 Accepted` and `execution_result: task_id, buyer_secret, status: "in_progress", created_at, deadline_at`
    - Note: `deadline_at` is set based on task complexity (default: created_at + 60 seconds for simple tasks, up to hours for complex tasks)
    - Note: Payment is recorded as used to prevent double-spending
8. **NewsAgent** proceeds to execute the task asynchronously:
    * Uses any provided `secrets` securely (e.g., API keys for news APIs), ensuring they are never logged
    * Performs the actual work (searches news sources, retrieves articles)
    * Constructs the result data
    * Updates task status to `done` when complete, or `failed` on error
9. **ButlerAgent** polls **NewsAgent** at `/tasks/{task_id}` endpoint with `X-Buyer-Secret: {buyer_secret}` header
10. **NewsAgent** responds with `execution_result: task_id, buyer_secret, status: "in_progress"|"done"|"failed", data, created_at, deadline_at`
    - If `status: "done"`, `data` contains the result
    - If `status: "failed"`, `error` contains error details
    - If deadline exceeded, **NewsAgent** returns `status: "failed"` with appropriate error (see Deadline Handling below)

**Error Cases:**
* Rate limit exceeded → `429 Too Many Requests` with error code `RATE_LIMIT_EXCEEDED`
* Payment proof invalid or expired → `402 Payment Required` with error code `INVALID_PAYMENT_PROOF` and descriptive error details.
* Invalid `buyer_secret` for polling → `403 Forbidden`
* Task deadline exceeded → `status: "failed"` in polling response (see Deadline Handling below)
* Seller shutdown/internal error after payment → See Deadline Handling below

### 3.4 Error Scenarios

#### 3.4.1 Payment Expiration

**Scenario:** Buyer receives 402 Payment Required but payment takes too long, payment requirements expire.

**Steps:**
1. **Buyer** receives `402 Payment Required` with x402 payment requirements
2. **Buyer** initiates payment but payment service is slow
3. By the time **Buyer** obtains `payment_payload` and retries, payment requirements have expired
4. **Buyer** sends `execution_request` with `X-PAYMENT` header
5. **Seller** validates payment and rejects with `402 Payment Required` and error code `INVALID_PAYMENT_PROOF`
6. **Buyer** must request new payment requirements (by sending `execution_request` again without `X-PAYMENT` header)

#### 3.4.2 Deadline Handling and Seller Failure

**Scenario:** Seller fails to complete task before deadline, or Seller shuts down after payment is made.

**Problem Statement:**
When a Seller accepts payment but fails to deliver (due to deadline expiration, shutdown, or internal errors), the Buyer has paid but received no result. This creates a trust and economic problem.

**Recommended Approach for MVP:**
- **Primary**: Reputation Penalty Only (First iteration) - SearchEngineBK tracks Seller completion rates, adjusts rankings accordingly.
- **Future**: Automatic Refund (Option 1) and Escrow Service (Option 5)

**Implementation Requirements:**
- Sellers MUST track payment → task mapping
- Sellers MUST set realistic `deadline_at` based on task complexity
- Buyers MUST poll until deadline or completion
- If Seller shuts down after payment but before completion, Buyer should report to SearchEngineBK for reputation tracking


## 4. Non-Functional Requirements


### 4.1 Security

* **HTTPS Enforcement**: All `base_url`s must use HTTPS. TLS certificate validation must be strict in production (optional in development for testing).
* **Payment Proof Validation**: Payment proof validation must be cryptographically secure. Sellers must verify transaction with use of x402 protocol
* **Secrets Handling**: Sensitive data (`secrets`) must never be logged by Seller agents. Secrets must be masked in error messages and excluded from any logging output.
* **Rate Limiting**: Rate limiting should be implemented to prevent abuse:
    * `/register`: 10 requests per minute per agent
    * `/search`: 60 requests per minute per agent (SearchEngineBK)
    * `/execute`: 100 requests per minute per agent (Seller endpoints)
    * `/tasks/{task_id}` (polling): 30 requests per minute per `buyer_secret` (SearchEngineBK and Seller endpoints)

### 4.2 Performance
* **Task Search Latency**: **SearchEngineBK** should respond to `search_request` within **< 500ms** (P95) for typical queries under normal load.
* **Execution Latency**: For synchronous tasks, Sellers should respond to `/execute` within **< 60 seconds**; longer tasks MUST use the async pattern described in Future Enhancements.
* **Throughput Targets**: The system should be able to handle **hundreds of concurrent search requests** and **tens of concurrent executions per Seller** without degradation beyond agreed SLAs.

### 4.3 Reliability

* MarketplaceBK should be highly available (target: 99.9% uptime).
* SearchEngineBK should implement retry logic for MarketplaceBK API calls.
* Buyer agents should implement retry logic for Seller execution requests.

### 4.4 Observability

* All services should log requests and responses (excluding sensitive data).
* MarketplaceBK should track metrics: agent registrations.
* Seller agents should track metrics: tasks received, executions completed.
* SearchEngineBK should track metrics: number of `search_request` calls, search latency distributions, result set sizes, and downstream Seller selection/conversion rates (how often a returned Seller is actually hired).

### 4.5 Idempotency

* Registration updates should be idempotent (same `seller_id` with same data should not create duplicates).
* Payment proof validation should handle duplicate requests gracefully.

### 4.6 Scalability

* SearchEngineBK should handle hundreds of concurrent searchs.
* The system should support thousands of registered Seller agents.


## 5. Future Enhancements

### 5.1 Persistent Storage (PostgreSQL)

Migrating from JSON-based persistence to a robust PostgreSQL database for MarketplaceBK and SearchEngineBK to handle scale and improve reliability.

*   [ ] **Design Database Schema**: Create schemas for `agents` (Marketplace) and `poll_state` (SearchEngine).
*   [ ] **Marketplace Migration**:
    *   Update `MarketplaceBK` to use `asyncpg` or `SQLAlchemy` (async).
    *   Implement `PostgresAgentRepository` matching the repository interface.
    *   Add migration scripts (e.g., using `alembic`).
*   [ ] **SearchEngine Migration**:
    *   Update `MarketplacePoller` to store offsets in Postgres.
    *   (Optional) Consider moving vector metadata to Postgres if Qdrant payload search becomes limiting.
*   [ ] **Integration Testing**: Verify data persists across container rebuilds using a real Postgres service in `docker-compose`.

### 5.2 Advanced Search & Filtering

Enable more granular discovery of agents based on specific criteria beyond semantic similarity.

*   [ ] **Implement Tags**:
    *   Update `AgentProfile` to strictly validate tags.
    *   Update `SearchRequest` to accept a list of `tags`.
    *   Modify `QdrantService` to use Qdrant's payload filtering for tags.
*   [ ] **Budget Filtering**:
    *   Standardize a `price_range` field in `SellerProfile` (derived from their `tool_pricing.yaml`).
    *   Update `SearchRequest` to accept `budget_range`.
    *   Implement numeric range filtering in `QdrantService`.

### 5.3 Reputation System

A reputation system could track Seller performance (execution success rate, response time) and Buyer reliability (payment success rate). This data could affect search results to help Buyers make better selection decisions.

*   [ ] **Feedback Loop**:
    *   Implement a mechanism for Buyers to report task outcomes (success/failure) to `MarketplaceSC`.
    *   Secure this endpoint (prevent spam/abuse).
*   [ ] **Reputation Score**:
    *   Calculate a reliability score (e.g., success rate over last N tasks).
    *   Update `QdrantService` to boost ranking of agents with high scores.
*   [ ] **Health Check Monitoring**:
    *   Sellers should periodically "ping" `MarketplaceSC` to be listed as the active ones.

### 5.4 Promotion System

Search results could be affected by promotion tools (inspired by real-world services like CIAN.ru, profi.ru, avito, etc.) such as:
- First week registration buff
- Paid Promotion (guarantee to appear in <K> search requests per week)
- Reputation Boosts (higher placement for Sellers with consistently high evaluation scores and low failure rates)
- Category Spotlights (temporary boosts for Sellers in under-served tags/topics to increase marketplace coverage)

### 5.5 Escrow Service & Refunds

For high-value transactions, an escrow service could be implemented where:
* Third-party escrow holds payment until task completion
* Automatic refund on deadline expiration
* Additional security and trust guarantees for Buyers

*   [ ] **Escrow Service (Long Term)**:
    *   Design a smart contract or trusted intermediary service for high-value tasks.

### 5.6 Agentic Behavior Improvements

Make Seller Agents smarter and more autonomous.

*   [ ] **Dynamic Pricing Logic**:
    *   Implement logic in Seller to adjust pricing based on current load, token costs, or task complexity (instead of static YAML).

### 5.7 Developer Experience & CI/CD

Make it easier for third parties to build and deploy agents.

*   [ ] **SDK Publishing**: Publish `xy_market` to a private or public PyPI repository.
*   [ ] **Comprehensive E2E Test Suite**: Expand the current smoke tests into a full regression suite running in CI (GitHub Actions/GitLab CI).

### 5.8 Security Audits

*   [ ] **Rate Limiting Tuning**: Adjust rate limits based on real-world usage patterns.

