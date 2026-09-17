"""Todo tests."""

import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient, email: str = "todo@example.com") -> str:
    """Helper to register and get auth token."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_create_todo(client: AsyncClient):
    """Test creating a new todo."""
    token = await get_auth_token(client, "create@example.com")

    response = await client.post(
        "/api/v1/todos",
        json={"title": "Test Todo", "description": "A test todo item"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Todo"
    assert data["description"] == "A test todo item"
    assert data["completed"] is False


@pytest.mark.asyncio
async def test_get_todos(client: AsyncClient):
    """Test getting todo list."""
    token = await get_auth_token(client, "list@example.com")

    # Create a todo first
    await client.post(
        "/api/v1/todos",
        json={"title": "List Todo"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Get todos
    response = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_update_todo(client: AsyncClient):
    """Test updating a todo."""
    token = await get_auth_token(client, "update@example.com")

    # Create a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Update Me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Update it
    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Updated Title", "completed": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_todo(client: AsyncClient):
    """Test deleting a todo."""
    token = await get_auth_token(client, "delete@example.com")

    # Create a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Delete Me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Delete it
    response = await client.delete(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_single_todo(client: AsyncClient):
    """Test getting a single todo by ID."""
    token = await get_auth_token(client, "single@example.com")

    # Create a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Single Todo", "description": "Get me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Get it
    response = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Single Todo"


@pytest.mark.asyncio
async def test_user_a_cannot_read_user_b_todo(client: AsyncClient):
    """Test authorization: User A cannot read User B's todos."""
    # User A creates a todo
    token_a = await get_auth_token(client, "usera@example.com")
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "User A's Todo"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    todo_id = create_response.json()["id"]

    # User B tries to read User A's todo
    token_b = await get_auth_token(client, "userb@example.com")
    response = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_update_user_b_todo(client: AsyncClient):
    """Test authorization: User A cannot update User B's todos."""
    # User A creates a todo
    token_a = await get_auth_token(client, "usera2@example.com")
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "User A's Todo"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    todo_id = create_response.json()["id"]

    # User B tries to update User A's todo
    token_b = await get_auth_token(client, "userb2@example.com")
    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Hacked", "completed": True},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_user_a_cannot_delete_user_b_todo(client: AsyncClient):
    """Test authorization: User A cannot delete User B's todos."""
    # User A creates a todo
    token_a = await get_auth_token(client, "usera3@example.com")
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "User A's Todo"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    todo_id = create_response.json()["id"]

    # User B tries to delete User A's todo
    token_b = await get_auth_token(client, "userb3@example.com")
    response = await client.delete(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_toggle_completed_true_to_false_persists(client: AsyncClient):
    """Test boolean toggle: updating completed from true back to false persists correctly."""
    token = await get_auth_token(client, "toggle@example.com")

    # Create a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Toggle Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Mark as completed (true)
    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"completed": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["completed"] is True

    # Mark as not completed (false)
    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"completed": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["completed"] is False

    # Verify it persists by fetching again
    response = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["completed"] is False


@pytest.mark.asyncio
async def test_partial_update_title_does_not_erase_description(client: AsyncClient):
    """Test incomplete partial update: updating title does not erase description."""
    token = await get_auth_token(client, "partial@example.com")

    # Create a todo with description
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Original Title", "description": "Important description"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Update only the title
    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Updated Title"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "Important description"  # Description preserved


@pytest.mark.asyncio
async def test_cache_invalidation_on_create_update_delete(client: AsyncClient):
    """Test cache invalidation: creating, updating, or deleting a todo removes stale cache."""
    token = await get_auth_token(client, "cache@example.com")

    # Get initial list (populates cache)
    response = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    initial_total = response.json()["total"]

    # Create a new todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "New Todo for Cache Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_response.status_code == 201

    # Get list again - should reflect new todo (cache invalidated)
    response = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    new_total = response.json()["total"]
    assert new_total == initial_total + 1

    # Update the todo
    todo_id = create_response.json()["id"]
    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Updated for Cache Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200

    # Get list again - should reflect update
    response = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    updated_todo = response.json()["items"][0]
    assert updated_todo["title"] == "Updated for Cache Test"

    # Delete the todo
    response = await client.delete(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204

    # Get list again - should reflect deletion
    response = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    final_total = response.json()["total"]
    assert final_total == initial_total
