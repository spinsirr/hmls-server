import pytest
from httpx import AsyncClient
import asyncio
from datetime import datetime

pytestmark = pytest.mark.asyncio

async def test_register_user(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/register",
        json={
            "email": "newuser@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "phone_number": "+12345678901",
            "password": "testpass123",
            "vehicle_year": "2020",
            "vehicle_make": "Toyota",
            "vehicle_model": "Camry",
            "vehicle_vin": "1HGCM82633A123456"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert data["is_active"] is True

async def test_register_duplicate_email(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/register",
        json={
            "email": "test@example.com",
            "first_name": "Jane",
            "last_name": "Smith",
            "phone_number": "+12345678902",
            "password": "testpass123",
            "vehicle_year": "2021",
            "vehicle_make": "Honda",
            "vehicle_model": "Civic",
            "vehicle_vin": "2HGES16575H123456"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

async def test_login_success(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/token",
        data={
            "username": "test@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_login_wrong_password(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/token",
        data={
            "username": "test@example.com",
            "password": "wrongpass"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

async def test_login_nonexistent_user(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/token",
        data={
            "username": "nonexistent@example.com",
            "password": "testpass123"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

async def test_registration_pressure(async_client: AsyncClient):
    # Test concurrent registrations
    async def register_user(i: int):
        return await async_client.post(
            "/auth/register",
            json={
                "email": f"user{i}@example.com",
                "first_name": f"User{i}",
                "last_name": "Test",
                "phone_number": f"+1234567{i:04d}",
                "password": "testpass123",
                "vehicle_year": "2020",
                "vehicle_make": "Toyota",
                "vehicle_model": "Camry",
                "vehicle_vin": f"1HGCM82633A{i:06d}"
            }
        )
    
    # Create 50 concurrent registration requests
    tasks = [register_user(i) for i in range(50)]
    responses = await asyncio.gather(*tasks)
    
    # Check results
    success_count = sum(1 for r in responses if r.status_code == 200)
    assert success_count == 50, f"Expected 50 successful registrations, got {success_count}"

async def test_login_pressure(async_client: AsyncClient):
    # First create test users
    async def create_test_user(i: int):
        return await async_client.post(
            "/auth/register",
            json={
                "email": f"loginuser{i}@example.com",
                "first_name": f"User{i}",
                "last_name": "Test",
                "phone_number": f"+1234567{i:04d}",
                "password": "testpass123",
                "vehicle_year": "2020",
                "vehicle_make": "Toyota",
                "vehicle_model": "Camry",
                "vehicle_vin": f"1HGCM82633A{i:06d}"
            }
        )
    
    # Create 10 test users
    user_count = 10
    create_tasks = [create_test_user(i) for i in range(user_count)]
    create_responses = await asyncio.gather(*create_tasks)
    
    # Verify users were created
    success_count = sum(1 for r in create_responses if r.status_code == 200)
    assert success_count == user_count, f"Failed to create test users. Only created {success_count} of {user_count}"
    
    # Test concurrent logins
    async def login_user(i: int):
        return await async_client.post(
            "/auth/token",
            data={
                "username": f"loginuser{i % user_count}@example.com",
                "password": "testpass123"
            }
        )
    
    # Create 100 concurrent login requests
    login_count = 100
    login_tasks = [login_user(i) for i in range(login_count)]
    login_responses = await asyncio.gather(*login_tasks)
    
    # Check results
    success_count = sum(1 for r in login_responses if r.status_code == 200)
    assert success_count == login_count, f"Expected {login_count} successful logins, got {success_count}" 