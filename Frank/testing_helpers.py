TEST_PASSWORD = "TestPass1!"


def register_test_user(
    client,
    email="owner@example.com",
    first_name="Test",
    last_name="User",
):
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 201, response.get_json()
    return response
