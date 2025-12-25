## Abstractions

### Plugin Abstraction:

- MUST support MCP protocol
- MUST support x402 protocol for paid endpoints
- MUST provide following endpoints:
	-   `\pricing` - exposes underlaying tool pricing configuration 
- MAY support Restful API 
- MAY have connected MCP plugins
- MAY have NLP engine inside 

### Seller Abstraction

 - MUST support MCP protocol
 - MUST support x402 protocol for paid endpoints
 - MUST provide following endpoints:
	 -  `\pricing` - exposes underlaying tool pricing configuration 
	-  `\execute` - accept incoming task requests
	-  `\tasks\{task_id}` - provides tasks completion results after processing
- MAY support Restful API 
- MAY have connected MCP plugins
- MUST have NLP engine inside

TODO: how should we organize mcp-servers repository?
Should we include our xy_market shared library there?
Should be upgrade those MCP to become actual sellers, or could we stay as xyber-independent MCP's?