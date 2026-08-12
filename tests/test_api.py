import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_list_templates(client):
    response = await client.get("/api/v1/templates/")
    assert response.status_code == 200
    data = response.json()
    assert "templates" in data
    assert data["total"] > 0


@pytest.mark.asyncio
async def test_create_and_get_letter(client):
    payload = {
        "type": "love",
        "template_id": "mailbox",
        "from_name": "Alex",
        "to_name": "Mia",
        "message": "My dearest Mia, from the very first day we met...",
        "photos": ["/uploads/sample1.jpg"],
        "song_id": "honeymoon",
        "song_title": "Honeymoon Avenue",
        "song_artist": "Ariana Grande",
        "delivery_method": "link"
    }

    # Create letter
    response = await client.post("/api/v1/letters/", json=payload)
    assert response.status_code == 201
    letter = response.json()
    assert letter["from_name"] == "Alex"
    assert letter["to_name"] == "Mia"
    assert "slug" in letter
    slug = letter["slug"]

    # Fetch letter by slug
    get_res = await client.get(f"/api/v1/letters/{slug}")
    assert get_res.status_code == 200
    fetched = get_res.json()
    assert fetched["slug"] == slug
    assert fetched["message"] == payload["message"]


@pytest.mark.asyncio
async def test_featured_music(client):
    response = await client.get("/api/v1/music/featured")
    assert response.status_code == 200
    tracks = response.json()
    assert len(tracks) > 0
    assert "title" in tracks[0]


@pytest.mark.asyncio
async def test_schedule_delivery(client, signed_in):
    # First create letter (attached to the session, so it can be re-targeted)
    payload = {
        "type": "birthday",
        "template_id": "birthday-mailbox",
        "from_name": "Sam",
        "to_name": "Taylor",
        "message": "Happy Birthday Taylor! Wishing you an amazing year ahead!",
        "delivery_method": "link"
    }
    create_res = await client.post("/api/v1/letters/", json=payload)
    letter = create_res.json()
    slug = letter["slug"]

    # Schedule delivery
    delivery_payload = {
        "letter_slug": slug,
        "method": "email",
        "contact": "taylor@example.com"
    }
    delivery_res = await client.post("/api/v1/delivery/schedule", json=delivery_payload)
    assert delivery_res.status_code == 200
    res_data = delivery_res.json()
    assert res_data["success"] is True
    assert res_data["method"] == "email"


@pytest.mark.asyncio
async def test_schedule_delivery_requires_ownership(client, signed_in):
    """Otherwise anyone could point any letter's SMS and voice delivery at a
    number of their choosing, billed to our gateway account."""
    slug = (
        await client.post(
            "/api/v1/letters/",
            json={"from_name": "Sam", "to_name": "Taylor", "message": "Hi", "delivery_method": "link"},
        )
    ).json()["slug"]

    client.cookies.clear()
    res = await client.post(
        "/api/v1/delivery/schedule",
        json={"letter_slug": slug, "method": "sms", "contact": "+15550100"},
    )
    assert res.status_code == 401
