@e2e
Feature: Service Health Checks
    As an operator of the PROOF ecosystem
    I want to verify that all services are healthy
    So that I can ensure the system is ready for operations

    Scenario: All core services are reachable
        Given the Marketplace service is running
        And the Seller service is running
        And the MCP Server service is running
        And the Buyer service is running
        Then all services should respond to health checks
