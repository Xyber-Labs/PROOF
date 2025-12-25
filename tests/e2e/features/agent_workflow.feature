@e2e
Feature: Full PROOF Ecosystem Workflow
    As a buyer agent in the PROOF ecosystem
    I want to discover sellers via marketplace and execute tasks using MCP tools
    So that I can complete my objectives using the decentralized agent marketplace

    Background:
        Given all services are healthy

    # -------------------------------------------------------------------------
    # Seller Auto-Registration Flow
    # -------------------------------------------------------------------------
    Scenario: Seller auto-registers with marketplace on startup
        Given the Seller service is running
        And the Marketplace service is running
        And a seller agent is registered with the marketplace
        Then the seller should be discoverable via marketplace
        And the seller profile should contain valid metadata

    # -------------------------------------------------------------------------
    # Seller-MCP Server Integration
    # -------------------------------------------------------------------------
    Scenario: Seller discovers and connects to MCP servers
        Given the Seller service is running
        And the MCP Server service is running
        When I request the seller's available tools
        Then the seller should expose MCP server tools
        And the tool list should include weather tools

    # -------------------------------------------------------------------------
    # Buyer Discovery Flow
    # -------------------------------------------------------------------------
    Scenario: Buyer discovers sellers via marketplace
        Given a seller agent is registered with the marketplace
        When the buyer queries the marketplace for available sellers
        Then the buyer should receive a list of sellers
        And each seller should have pricing information

    # -------------------------------------------------------------------------
    # Full E2E Task Execution
    # -------------------------------------------------------------------------
    Scenario: End-to-end task execution through the ecosystem
        Given all services are healthy
        And a seller agent is registered with the marketplace
        When the buyer discovers sellers via marketplace
        And the buyer initiates a task with a seller
        And I poll until execution completes
        Then the execution should succeed or require payment

    # -------------------------------------------------------------------------
    # Authentication & Security
    # -------------------------------------------------------------------------
    Scenario: Execution polling requires valid authentication
        Given a task execution has been initiated
        When I poll with the correct buyer secret
        Then I should receive the task status
        When I poll with an incorrect buyer secret
        Then I should receive an authentication error
        When I poll without any buyer secret
        Then I should receive an authentication error

    # -------------------------------------------------------------------------
    # x402 Payment Flow (requires wallet configuration)
    # -------------------------------------------------------------------------
    @payment
    Scenario: Buyer pays seller via x402 protocol
        Given the buyer has a configured wallet
        And a seller agent is registered with the marketplace
        And the seller has paid endpoints
        When the buyer initiates a paid task with the seller
        Then the x402 payment should be processed
        And the task execution should proceed after payment
