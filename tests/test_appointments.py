import pytest
from httpx import AsyncClient, Response
import asyncio
from datetime import datetime, timedelta
import pytz
import json
from app.models.appointment import Appointment
import random

pytestmark = pytest.mark.asyncio

# Helper function to get auth token
async def get_auth_token(async_client: AsyncClient) -> str:
    response = await async_client.post(
        "/auth/token",
        data={
            "username": "test@example.com",
            "password": "testpass123"
        }
    )
    return response.json()["access_token"]

@pytest.fixture
async def auth_headers(async_client: AsyncClient) -> dict:
    token = await get_auth_token(async_client)
    return {"Authorization": f"Bearer {token}"}

async def wait_for_appointments(async_client: AsyncClient, auth_headers: dict, expected_count: int, timeout: int = 10) -> bool:
    """Wait for appointments to be processed"""
    start_time = datetime.now()
    while (datetime.now() - start_time).seconds < timeout:
        response = await async_client.get("/appointments/", headers=auth_headers)
        if response.status_code == 200:
            appointments = response.json()
            if len(appointments) >= expected_count:
                return True
        await asyncio.sleep(0.5)
    return False

async def test_create_appointment(async_client: AsyncClient, auth_headers: dict):
    appointment_time = datetime.now(pytz.UTC) + timedelta(days=1)
    response = await async_client.post(
        "/appointments/",
        headers=auth_headers,
        json={
            "email": "test@example.com",
            "phone_number": "+12345678901",
            "appointment_time": appointment_time.isoformat(),
            "vehicle_year": "2020",
            "vehicle_make": "Toyota",
            "vehicle_model": "Camry",
            "problem_description": "Regular maintenance"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert "queue_position" in data
    
    # Wait for appointment to be processed
    assert await wait_for_appointments(async_client, auth_headers, 1)
    
    # Verify appointment was created
    response = await async_client.get("/appointments/", headers=auth_headers)
    assert response.status_code == 200
    appointments = response.json()
    assert len(appointments) == 1
    assert appointments[0]["email"] == "test@example.com"
    assert appointments[0]["status"] == "pending"

async def test_create_appointment_past_time(async_client: AsyncClient, auth_headers: dict):
    appointment_time = datetime.now(pytz.UTC) - timedelta(days=1)
    response = await async_client.post(
        "/appointments/",
        headers=auth_headers,
        json={
            "email": "test@example.com",
            "phone_number": "+12345678901",
            "appointment_time": appointment_time.isoformat(),
            "vehicle_year": "2020",
            "vehicle_make": "Toyota",
            "vehicle_model": "Camry",
            "problem_description": "Regular maintenance"
        }
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Appointment time must be in the future"

async def test_get_appointments(async_client: AsyncClient, auth_headers: dict):
    # First create an appointment
    appointment_time = datetime.now(pytz.UTC) + timedelta(days=1)
    response = await async_client.post(
        "/appointments/",
        headers=auth_headers,
        json={
            "email": "test@example.com",
            "phone_number": "+12345678901",
            "appointment_time": appointment_time.isoformat(),
            "vehicle_year": "2020",
            "vehicle_make": "Toyota",
            "vehicle_model": "Camry",
            "problem_description": "Regular maintenance"
        }
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"
    
    # Wait for appointment to be processed
    assert await wait_for_appointments(async_client, auth_headers, 1)
    
    # Then get all appointments
    response = await async_client.get("/appointments/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["email"] == "test@example.com"

async def test_get_appointment_by_id(async_client: AsyncClient, auth_headers: dict):
    # First create an appointment
    appointment_time = datetime.now(pytz.UTC) + timedelta(days=2)
    create_response = await async_client.post(
        "/appointments/",
        headers=auth_headers,
        json={
            "email": "test@example.com",
            "phone_number": "+12345678901",
            "appointment_time": appointment_time.isoformat(),
            "vehicle_year": "2020",
            "vehicle_make": "Toyota",
            "vehicle_model": "Camry",
            "problem_description": "Regular maintenance"
        }
    )
    appointment_id = create_response.json()["id"]
    
    # Then get it by ID
    response = await async_client.get(f"/appointments/{appointment_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == appointment_id

async def test_update_appointment_status(async_client: AsyncClient, auth_headers: dict):
    # First create an appointment
    appointment_time = datetime.now(pytz.UTC) + timedelta(days=3)
    create_response = await async_client.post(
        "/appointments/",
        headers=auth_headers,
        json={
            "email": "test@example.com",
            "phone_number": "+12345678901",
            "appointment_time": appointment_time.isoformat(),
            "vehicle_year": "2020",
            "vehicle_make": "Toyota",
            "vehicle_model": "Camry",
            "problem_description": "Regular maintenance"
        }
    )
    appointment_id = create_response.json()["id"]
    
    # Update status to confirmed
    response = await async_client.put(
        f"/appointments/{appointment_id}",
        headers=auth_headers,
        json={"status": "confirmed"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "confirmed"

async def test_cancel_appointment(async_client: AsyncClient, auth_headers: dict):
    # First create an appointment
    appointment_time = datetime.now(pytz.UTC) + timedelta(days=4)
    create_response = await async_client.post(
        "/appointments/",
        headers=auth_headers,
        json={
            "email": "test@example.com",
            "phone_number": "+12345678901",
            "appointment_time": appointment_time.isoformat(),
            "vehicle_year": "2020",
            "vehicle_make": "Toyota",
            "vehicle_model": "Camry",
            "problem_description": "Regular maintenance"
        }
    )
    appointment_id = create_response.json()["id"]
    
    # Cancel the appointment
    response = await async_client.delete(f"/appointments/{appointment_id}", headers=auth_headers)
    assert response.status_code == 204

async def test_appointments_pressure(async_client: AsyncClient, auth_headers: dict):
    # Test concurrent appointment creation
    async def create_appointment(i: int):
        appointment_time = datetime.now(pytz.UTC) + timedelta(days=5, hours=i)
        return await async_client.post(
            "/appointments/",
            headers=auth_headers,
            json={
                "email": f"user{i}@example.com",
                "phone_number": f"+1234567{i:04d}",
                "appointment_time": appointment_time.isoformat(),
                "vehicle_year": "2020",
                "vehicle_make": "Toyota",
                "vehicle_model": "Camry",
                "problem_description": f"Maintenance request {i}"
            }
        )
    
    # Create 50 concurrent appointment requests
    tasks = [create_appointment(i) for i in range(50)]
    responses = await asyncio.gather(*tasks)
    
    # Check that all requests were successful
    success_count = sum(1 for r in responses if r.status_code == 200)
    assert success_count == 50

    # Verify all responses have queue positions
    for response in responses:
        data = response.json()
        assert data["status"] == "queued"
        assert "queue_position" in data
    
    # Wait for all appointments to be processed
    assert await wait_for_appointments(async_client, auth_headers, 50, timeout=30)
    
    # Verify all appointments were created
    response = await async_client.get("/appointments/", headers=auth_headers)
    assert response.status_code == 200
    appointments = response.json()
    assert len(appointments) == 50

    # Test concurrent appointment retrievals with retries
    async def get_appointments_with_retry(max_retries=10, base_delay=0.1):
        last_exception = None
        for attempt in range(max_retries):
            try:
                # Add jitter to delay to prevent thundering herd
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.5)
                response = await async_client.get("/appointments/", headers=auth_headers)
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 429:  # Rate limit exceeded
                    # For rate limiting, use a longer delay
                    await asyncio.sleep(delay * 2)
                    continue
                elif response.status_code >= 500:  # Server errors
                    await asyncio.sleep(delay)
                    continue
                else:  # Client errors should not be retried
                    return response
            except Exception as e:
                last_exception = e
                await asyncio.sleep(delay)
                continue
        
        if last_exception:
            raise last_exception
        return None
    
    # Create 100 concurrent get requests with retries, but stagger them slightly
    tasks = []
    for i in range(100):
        # Add a small stagger between task creation
        if i > 0 and i % 10 == 0:  # Every 10 tasks
            await asyncio.sleep(0.001)  # Reduced delay to 1ms
        tasks.append(get_appointments_with_retry())
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Check results, excluding exceptions
    valid_responses = [r for r in responses if isinstance(r, Response) and r.status_code == 200]
    success_count = len(valid_responses)
    
    # Print error information for debugging
    error_responses = [r for r in responses if isinstance(r, Response) and r.status_code != 200]
    exceptions = [r for r in responses if isinstance(r, Exception)]
    
    if success_count < 100:
        print(f"\nError responses ({len(error_responses)}):")
        for r in error_responses[:5]:  # Show first 5 error responses
            print(f"Status code: {r.status_code}, Response: {r.text}")
        print(f"\nExceptions ({len(exceptions)}):")
        for e in exceptions[:5]:  # Show first 5 exceptions
            print(f"Exception: {str(e)}")
    
    assert success_count == 100, f"Expected 100 successful retrievals, got {success_count}" 