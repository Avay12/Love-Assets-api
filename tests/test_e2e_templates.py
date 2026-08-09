import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_e2e_love_letter_template_flow(client: AsyncClient):
    payload = {
        "template_id": "mailbox",
        "from_name": "Alex",
        "to_name": "Mia",
        "message": "My dearest Mia, from the very first day we met...",
        "photos": ["https://example.com/photo1.jpg"],
        "song_id": "honeymoon",
        "song_title": "Honeymoon Avenue",
        "song_artist": "Ariana Grande",
        "delivery_method": "link",
        "details": {}
    }

    res = await client.post("/api/v1/love-letters/", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["template_id"] == "mailbox"
    assert data["type"] == "love"
    assert data["from_name"] == "Alex"
    assert data["to_name"] == "Mia"

    slug = data["slug"]
    get_res = await client.get(f"/api/v1/love-letters/{slug}")
    assert get_res.status_code == 200
    assert get_res.json()["slug"] == slug


@pytest.mark.asyncio
async def test_e2e_birthday_letter_template_flow(client: AsyncClient):
    payload = {
        "template_id": "birthday-mailbox",
        "from_name": "Sam",
        "to_name": "Jordan",
        "message": "Happy Birthday Jordan! Wishing you a fantastic year ahead! 🎂",
        "photos": [],
        "delivery_method": "link",
        "details": {
            "celebrant_name": "Jordan Smith",
            "birth_date": "2000-05-15"
        }
    }

    res = await client.post("/api/v1/birthday-letters/", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["template_id"] == "birthday-mailbox"
    assert data["type"] == "birthday"
    assert data["details"]["celebrant_name"] == "Jordan Smith"
    assert data["details"]["turning_age"] == 26

    slug = data["slug"]
    get_res = await client.get(f"/api/v1/birthday-letters/{slug}")
    assert get_res.status_code == 200
    assert get_res.json()["slug"] == slug


@pytest.mark.asyncio
async def test_e2e_birthday_invite_template_flow(client: AsyncClient):
    payload = {
        "template_id": "invite-confetti",
        "from_name": "Airin",
        "to_name": "Chelsea Olyvia",
        "message": "Come celebrate my 17th birthday with me!",
        "photos": ["https://example.com/photo1.jpg", "https://example.com/photo2.jpg"],
        "song_id": "birds",
        "song_title": "Birds of a Feather",
        "song_artist": "Billie Eilish",
        "delivery_method": "link",
        "details": {
            "celebrant_name": "Chelsea Olyvia",
            "birth_date": "2009-08-08",
            "event_at": "2026-08-08T17:00:00+07:00",
            "date_line": "Saturday, 8 August 2026",
            "time_line": "17.00 WIB",
            "venue": {
                "name": "VERTE BISTRO",
                "address": [
                    "Ruko Icon Business Park E1, Sampora,",
                    "Kec. Cisauk, Kabupaten Tangerang,",
                    "Banten 15345"
                ],
                "maps_url": "https://maps.google.com/?q=Verte+Bistro"
            },
            "dress_code": "Pink, brown and white",
            "attendance_manager": "Airin",
            "attendance_manager_contact": "0811 2233 4455",
            "rsvp_deadline": "2026-08-05",
            "story": "Turning 17 feels so unreal honestly... Thank you for growing up with me! 🤍"
        }
    }

    # 1. POST request to create birthday invitation
    res = await client.post("/api/v1/birthday-invitations/", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["template_id"] == "invite-confetti"
    assert data["from_name"] == "Airin"
    assert data["to_name"] == "Chelsea Olyvia"
    assert data["details"]["celebrant_name"] == "Chelsea Olyvia"
    assert data["details"]["turning_age"] == 17
    assert data["details"]["dress_code"] == "Pink, brown and white"
    assert data["details"]["attendance_manager"] == "Airin"
    assert data["details"]["venue"]["name"] == "VERTE BISTRO"
    assert len(data["details"]["venue"]["address"]) == 3

    slug = data["slug"]

    # 2. GET request by slug to verify retrieval
    get_res = await client.get(f"/api/v1/birthday-invitations/{slug}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["slug"] == slug
    assert retrieved["message"] == "Come celebrate my 17th birthday with me!"
    assert retrieved["details"]["story"] == "Turning 17 feels so unreal honestly... Thank you for growing up with me! 🤍"


@pytest.mark.asyncio
async def test_e2e_wedding_invite_template_flow(client: AsyncClient):
    payload = {
        "template_id": "wedding-velvet",
        "from_name": "Dimas Tama",
        "to_name": "Tania Diandra",
        "message": "Dengan memohon rahmat & ridho Allah SWT, kami mengundang bapak/ibu/saudara/i...",
        "photos": ["https://example.com/bride.jpg", "https://example.com/groom.jpg"],
        "song_id": "ivy",
        "song_title": "Ivy",
        "song_artist": "Frank Ocean",
        "delivery_method": "email",
        "delivery_contact": "tania@example.com",
        "details": {
            "bride_parents": "Mr. & Mrs. Diandra",
            "groom_parents": "Mr. & Mrs. Tama",
            "event_at": "2026-08-08T09:00:00+07:00",
            "date_line": "Saturday, 8 August 2026",
            "akad_time": "09.00 WIB",
            "reception_time": "11.00 WIB",
            "venue": {
                "name": "PLATARAN DHARMAWANGSA",
                "address": [
                    "Jl. Dharmawangsa Raya No.6, RT.4/RW.2,",
                    "Kota Jakarta Selatan, Jakarta 12160"
                ],
                "maps_url": "https://maps.google.com/?q=Plataran"
            },
            "dress_code": "Formal Pastel",
            "gift_accounts": [
                {"bank": "BCA", "number": "1122334455", "holder": "Tania Diandra"},
                {"bank": "Mandiri", "number": "9988776655", "holder": "Dimas Tama"}
            ],
            "story": "Our journey together from day one to the altar..."
        }
    }

    # 1. POST request to create wedding invitation
    res = await client.post("/api/v1/wedding-invitations/", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["template_id"] == "wedding-velvet"
    assert data["from_name"] == "Dimas Tama"
    assert data["to_name"] == "Tania Diandra"
    assert data["details"]["bride_parents"] == "Mr. & Mrs. Diandra"
    assert data["details"]["groom_parents"] == "Mr. & Mrs. Tama"
    assert len(data["details"]["gift_accounts"]) == 2
    assert data["details"]["gift_accounts"][0]["bank"] == "BCA"

    slug = data["slug"]

    # 2. GET request by slug
    get_res = await client.get(f"/api/v1/wedding-invitations/{slug}")
    assert get_res.status_code == 200
    retrieved = get_res.json()
    assert retrieved["details"]["akad_time"] == "09.00 WIB"
    assert retrieved["details"]["reception_time"] == "11.00 WIB"


@pytest.mark.asyncio
async def test_e2e_empty_optional_fields_and_special_chars(client: AsyncClient):
    payload = {
        "template_id": "valentine-velvet",
        "from_name": "José & François <Special Characters test>",
        "to_name": "Aña ✨❤️",
        "message": "Testing special characters: ¡Hola! 💖 ~ ` ! @ # $ % ^ & * ( ) _ + - = { } [ ] : ; \" ' < > ? / \\ |",
        "photos": [],
        "delivery_method": "link",
        "details": {
            "date_night": None,
            "rsvp_enabled": True
        }
    }

    res = await client.post("/api/v1/valentine-letters/", json=payload)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["from_name"] == "José & François <Special Characters test>"
    assert data["to_name"] == "Aña ✨❤️"
    assert "¡Hola! 💖" in data["message"]
