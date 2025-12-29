## Abstractions

### Plugin Abstraction:

- MUST support MCP protocol
- MAY support x402 protocol for paid endpoints
- MAY provide following endpoints:
	-   `\pricing` - exposes underlaying tool pricing configuration 
- MAY support Restful API 

### Seller Abstraction

 - MUST support MCP protocol
 - MUST support x402 protocol for paid endpoints
 - MUST provide following endpoints:
	 -  `\pricing` - exposes underlaying tool pricing configuration 
	-  `\execute` - accept incoming task requests
	-  `\tasks\{task_id}` - provides tasks completion results after processing
- MAY support Restful API 
- MAY have connected MCP plugins

