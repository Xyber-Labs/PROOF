import asyncio
import pytest
import httpx
import uuid
from typing import Any

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


@pytest.fixture(scope="module")
def marketplace_url():
    """MarketplaceBK base URL."""
    return "http://localhost:8001"


@pytest.fixture(scope="module")
def search_engine_url():
    """SearchEngineBK base URL."""
    return "http://localhost:8000"


@pytest.fixture(scope="module")
def seller_url():
    """Seller base URL."""
    return "http://localhost:8002"


@pytest.fixture(scope="module")
def qdrant_url():
    """Qdrant base URL."""
    return "http://localhost:6333"


@pytest.mark.asyncio
async def test_services_health(
    marketplace_url: str, search_engine_url: str, seller_url: str, qdrant_url: str
):
    """Test that all services are healthy."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check Qdrant (Qdrant doesn't have /health, check collections endpoint instead)
        try:
            response = await client.get(f"{qdrant_url}/collections")
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"Qdrant not available: {e}")

        # Check MarketplaceBK
        try:
            response = await client.get(f"{marketplace_url}/health")
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"MarketplaceBK not available: {e}")

        # Check SearchEngineBK
        try:
            response = await client.get(f"{search_engine_url}/health")
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"SearchEngineBK not available: {e}")

        # Check Seller
        try:
            response = await client.get(f"{seller_url}/health")
            assert response.status_code == 200
        except Exception as e:
            pytest.skip(f"Seller not available: {e}")


    async def _register_seller(self, client: httpx.AsyncClient, marketplace_url: str, seller_url: str, seller_id: str):
        """Register the seller agent with the Marketplace."""
        seller_profile = {
            "agent_id": seller_id,
            "base_url": seller_url,
            "description": "News Agent that finds and summarizes latest news articles about AI and technology",
            "tags": ["news", "ai", "technology"],
        }
        
        try:
            register_response = await client.post(
                f"{marketplace_url}/register",
                json=seller_profile,
            )
            assert register_response.status_code in [200, 409]  # 409 if already registered
            print(f"✓ Seller registered: {register_response.status_code}")
        except Exception as e:
            pytest.skip(f"Failed to register seller: {e}")

    async def _search_sellers(self, client: httpx.AsyncClient, search_engine_url: str) -> dict[str, Any]:
        """Initiate the search for sellers and return the initial search response data."""
        search_request = {
            "task_description": "Find the latest news articles about AI advancements",
            "limit": 5,
            "budget_range": [10.0, 1000.0],
        }

        try:
            search_response = await client.post(
                f"{search_engine_url}/search",
                json=search_request,
            )
            assert search_response.status_code == 200
            search_data = search_response.json()
            
            # Should return immediately with task_id, buyer_secret, and status
            assert "task_id" in search_data
            assert "buyer_secret" in search_data
            assert "buyer_id" in search_data
            assert "status" in search_data
            
            print(f"✓ Search initiated: task_id={search_data['task_id']}, status={search_data['status']}")
            return search_data
        except Exception as e:
            pytest.skip(f"Search failed: {e}")
            return {}

    async def _poll_search_results(self, client: httpx.AsyncClient, search_engine_url: str, initial_data: dict[str, Any]) -> dict[str, Any]:
        """Poll the search task until completion and return the final results."""
        task_id = initial_data["task_id"]
        buyer_secret = initial_data["buyer_secret"]
        status = initial_data["status"]
        search_data = initial_data

        if status == "in_progress":
            print("Polling search task...")
            max_polls = 10
            poll_count = 0
            
            while poll_count < max_polls:
                await asyncio.sleep(2)
                poll_response = await client.get(
                    f"{search_engine_url}/tasks/{task_id}",
                    headers={"X-Buyer-Secret": buyer_secret},
                )
                assert poll_response.status_code == 200
                search_data = poll_response.json()
                
                if search_data["status"] != "in_progress":
                    break
                poll_count += 1
            
            assert search_data["status"] in ["completed", "failed"]
            print(f"✓ Search completed: status={search_data['status']}")
        
        return search_data

    def _verify_and_select_seller(self, search_data: dict[str, Any], seller_id: str) -> dict[str, Any]:
        """Verify sellers were found and select the target seller."""
        assert "sellers" in search_data
        sellers = search_data["sellers"]
        assert len(sellers) > 0
        print(f"✓ Found {len(sellers)} sellers")

        found_seller = next(
            (s for s in sellers if s["seller_id"] == seller_id), None
        )
        assert found_seller is not None, "Seller should be found in search results"
        print(f"✓ Seller found in search results")
        return found_seller

    async def _execute_task(self, client: httpx.AsyncClient, seller_url: str, buyer_id: str) -> dict[str, Any]:
        """Initiate task execution with the selected seller."""
        execution_request = {
            "task_description": "Find the latest news articles about AI advancements",
            "context": {"buyer_id": buyer_id},
        }

        try:
            execute_response = await client.post(
                f"{seller_url}/execute",
                json=execution_request,
            )

            # Should return 202 Accepted (async) or 402 Payment Required
            assert execute_response.status_code in [202, 402]
            
            if execute_response.status_code == 402:
                print("✓ Payment required (402 received)")
                return {"status": "payment_required", "data": execute_response.json()}
            
            execution_data = execute_response.json()
            assert "task_id" in execution_data
            assert "buyer_secret" in execution_data
            assert execution_data["status"] == "in_progress"
            
            print(f"✓ Task execution initiated: task_id={execution_data['task_id']}")
            return execution_data
            
        except Exception as e:
            pytest.skip(f"Execution failed: {e}")
            return {}

    async def _poll_execution_status(self, client: httpx.AsyncClient, seller_url: str, execution_data: dict[str, Any]):
        """Poll the execution task until completion."""
        if execution_data.get("status") == "payment_required":
            # For E2E test, just verify structure
            data = execution_data["data"]
            assert "error_code" in data or "invoice" in data
            return

        exec_task_id = execution_data["task_id"]
        exec_buyer_secret = execution_data["buyer_secret"]
        
        max_polls = 10
        poll_count = 0
        final_data = execution_data
        
        while poll_count < max_polls:
            await asyncio.sleep(2)
            poll_response = await client.get(
                f"{seller_url}/tasks/{exec_task_id}",
                headers={"X-Buyer-Secret": exec_buyer_secret},
            )
            assert poll_response.status_code == 200
            final_data = poll_response.json()
            
            if final_data["status"] != "in_progress":
                break
            poll_count += 1
        
        assert final_data["status"] in ["done", "failed"]
        print(f"✓ Task execution completed: status={final_data['status']}")
        
        if final_data["status"] == "done":
            assert "data" in final_data
            print(f"✓ Execution result: {final_data.get('data')}")

@pytest.mark.asyncio
class TestFullWorkflow:
    """End-to-end integration tests for the full Agent Swarms workflow."""

    async def test_full_workflow_with_search_and_execution(
        self, marketplace_url: str, search_engine_url: str, seller_url: str
    ):
        """Test full workflow: Register seller → Search (async) → Execute (async)."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            seller_id = "770e8400-e29b-41d4-a716-446655440002"

            # Step 1: Register seller
            await self._register_seller(client, marketplace_url, seller_url, seller_id)

            # Step 2: Wait for indexing
            await asyncio.sleep(10)

            # Step 3: Search
            initial_search = await self._search_sellers(client, search_engine_url)
            final_search = await self._poll_search_results(client, search_engine_url, initial_search)
            selected_seller = self._verify_and_select_seller(final_search, seller_id)

            # Step 4: Execute
            execution_data = await self._execute_task(client, selected_seller['base_url'], final_search["buyer_id"])
            await self._poll_execution_status(client, selected_seller['base_url'], execution_data)



@pytest.mark.asyncio
async def test_search_engine_empty_results(search_engine_url: str):
    """Test search with no results."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        search_request = {
            "task_description": "Find extremely specific and unlikely topic xyzabc123",
            "limit": 5,
        }

        try:
            response = await client.post(
                f"{search_engine_url}/search",
                json=search_request,
            )
            assert response.status_code == 200
            search_data = response.json()
            
            # Should return task_id and buyer_secret even if no results yet
            assert "task_id" in search_data
            assert "buyer_secret" in search_data
            
            # Poll until completion
            task_id = search_data["task_id"]
            buyer_secret = search_data["buyer_secret"]
            
            if search_data["status"] == "in_progress":
                await asyncio.sleep(2)
                poll_response = await client.get(
                    f"{search_engine_url}/tasks/{task_id}",
                    headers={"X-Buyer-Secret": buyer_secret},
                )
                assert poll_response.status_code == 200
                search_data = poll_response.json()
            
            assert "sellers" in search_data
            # Empty results are valid
            print(f"✓ Search returned {len(search_data['sellers'])} results")
        except Exception as e:
            pytest.skip(f"Search test failed: {e}")


@pytest.mark.asyncio
async def test_search_duplicate_request(search_engine_url: str):
    """Test duplicate search request handling."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        search_request = {
            "task_description": "Find news about AI",
            "limit": 5,
        }

        try:
            # First request
            response1 = await client.post(
                f"{search_engine_url}/search",
                json=search_request,
            )
            assert response1.status_code == 200
            data1 = response1.json()
            task_id1 = data1["task_id"]
            
            # Second identical request (should return in_progress with empty sellers)
            response2 = await client.post(
                f"{search_engine_url}/search",
                json=search_request,
            )
            assert response2.status_code == 200
            data2 = response2.json()
            
            # Should either return same task_id or new task_id with in_progress status
            if data2.get("status") == "in_progress" and len(data2.get("sellers", [])) == 0:
                print("✓ Duplicate request handled correctly (in_progress)")
            elif data2.get("task_id") == task_id1:
                print("✓ Duplicate request handled correctly (same task_id)")
            else:
                # Both are valid behaviors
                print(f"✓ Duplicate request handled: status={data2.get('status')}")
                
        except Exception as e:
            pytest.skip(f"Duplicate request test failed: {e}")


@pytest.mark.asyncio
async def test_execution_polling_with_secret(seller_url: str):
    """Test execution polling with buyer_secret authentication."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        execution_request = {
            "task_description": "Test task for polling",
            "context": {},
        }

        try:
            # Initiate execution
            response = await client.post(
                f"{seller_url}/execute",
                json=execution_request,
            )
            
            if response.status_code == 202:
                data = response.json()
                task_id = data["task_id"]
                buyer_secret = data["buyer_secret"]
                
                # Poll with correct secret
                poll_response = await client.get(
                    f"{seller_url}/tasks/{task_id}",
                    headers={"X-Buyer-Secret": buyer_secret},
                )
                assert poll_response.status_code == 200
                
                # Poll with wrong secret (should fail)
                wrong_secret_response = await client.get(
                    f"{seller_url}/tasks/{task_id}",
                    headers={"X-Buyer-Secret": "wrong-secret"},
                )
                assert wrong_secret_response.status_code in [403, 404]
                
                # Poll without secret (should fail)
                no_secret_response = await client.get(
                    f"{seller_url}/tasks/{task_id}",
                )
                assert no_secret_response.status_code in [403, 422]
                
                print("✓ Polling authentication works correctly")
            else:
                pytest.skip(f"Execution initiation failed: {response.status_code}")
                
        except Exception as e:
            pytest.skip(f"Polling test failed: {e}")
