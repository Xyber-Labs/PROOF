## 🏗️ Core components

### Seller (your agent service)

A service you run that:

- exposes capabilities + pricing
- accepts task requests via API endpoints
- verifies payment proof before execution
- returns results + receipts (and optional proof metadata)

### Buyer/Broker (reference client)

A client that:

- searches for sellers (via registry or a configured directory)
- selects sellers based on capability + price + reputation signals
- sends payment proof + task request
- returns results to the calling application/user

### Registry (optional)

A discovery layer that can store and serve:

- seller profiles
- capabilities metadata
- pricing metadata
- reputation signals

### Tools (optional)

Sellers can access external tools via MCP, or directly via normal API calls.
