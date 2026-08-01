import io
import os

import pytest

BASE = {
    "template_id": "mailbox",
    "from_name": "Alex",
    "to_name": "Mia",
    "message": "Hello you.",
    "photos": [],
}

TYPE_PATHS = {
    "love": "/api/v1/love-letters",
    "valentine": "/api/v1/valentine-letters",
    "birthday": "/api/v1/birthday-letters",
    "birthday-invite": "/api/v1/birthday-invitations",
    "wedding": "/api/v1/wedding-invitations",
}


@pytest.mark.asyncio
@pytest.mark.parametrize("letter_type,path", TYPE_PATHS.items())
async def test_create_and_fetch_each_type(client, letter_type, path):
    res = await client.post(f"{path}/", json=BASE)
    assert res.status_code == 201, res.text
    body = res.json()

    assert body["type"] == letter_type
    assert body["slug"].startswith(
        {"love": "love", "valentine": "val", "birthday": "bday", "birthday-invite": "party", "wedding": "wed"}[
            letter_type
        ]
    )
    assert body["share_url"].endswith(f"/l/{body['slug']}")

    got = await client.get(f"{path}/{body['slug']}")
    assert got.status_code == 200
    assert got.json()["slug"] == body["slug"]


@pytest.mark.asyncio
async def test_type_endpoints_do_not_leak_across_types(client):
    made = await client.post("/api/v1/love-letters/", json=BASE)
    slug = made.json()["slug"]

    # a love letter must not be reachable through the wedding endpoint
    assert (await client.get(f"/api/v1/wedding-invitations/{slug}")).status_code == 404
    assert (await client.get(f"/api/v1/love-letters/{slug}")).status_code == 200


@pytest.mark.asyncio
async def test_birthday_invite_accepts_its_details(client):
    payload = {
        **BASE,
        "details": {
            "age": "17",
            "date_line": "Saturday, 8 August 2026",
            "time_line": "17.00 WIB",
            "venue": {
                "name": "VERTE BISTRO",
                "address": ["Ruko Icon Business Park E1, Sampora,", "Banten 15345"],
                "maps_url": "https://maps.google.com/?q=Verte+Bistro",
            },
        },
    }
    res = await client.post("/api/v1/birthday-invitations/", json=payload)
    assert res.status_code == 201, res.text
    details = res.json()["details"]
    assert details["age"] == "17"
    assert details["venue"]["name"] == "VERTE BISTRO"


@pytest.mark.asyncio
async def test_wedding_accepts_gift_accounts_and_story(client):
    payload = {
        **BASE,
        "details": {
            "akad_time": "09.00 WIB",
            "gift_accounts": [{"bank": "BCA", "number": "1122334455", "holder": "Tania Diandra"}],
            "story": [{"title": "Awal Pertemuan", "body": "Tidak ada yang benar-benar kebetulan."}],
        },
    }
    res = await client.post("/api/v1/wedding-invitations/", json=payload)
    assert res.status_code == 201, res.text
    details = res.json()["details"]
    assert details["gift_accounts"][0]["bank"] == "BCA"
    assert details["story"][0]["title"] == "Awal Pertemuan"


@pytest.mark.asyncio
async def test_unknown_detail_key_is_rejected(client):
    res = await client.post("/api/v1/love-letters/", json={**BASE, "details": {"age": "17"}})
    assert res.status_code == 422  # love letters take no details


@pytest.mark.asyncio
async def test_missing_required_field_is_rejected(client):
    res = await client.post("/api/v1/love-letters/", json={"from_name": "Alex"})
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_list_is_scoped_to_type(client):
    await client.post("/api/v1/love-letters/", json=BASE)
    await client.post("/api/v1/wedding-invitations/", json=BASE)

    loves = (await client.get("/api/v1/love-letters/")).json()
    assert loves["total"] == 1
    assert all(x["type"] == "love" for x in loves["letters"])


@pytest.mark.asyncio
async def test_delete(client):
    slug = (await client.post("/api/v1/birthday-letters/", json=BASE)).json()["slug"]
    assert (await client.delete(f"/api/v1/birthday-letters/{slug}")).status_code == 204
    assert (await client.get(f"/api/v1/birthday-letters/{slug}")).status_code == 404


@pytest.mark.asyncio
async def test_slugs_are_unique_across_many_creates(client):
    slugs = set()
    for _ in range(25):
        slugs.add((await client.post("/api/v1/love-letters/", json=BASE)).json()["slug"])
    assert len(slugs) == 25


# --------------------------------------------------------------------------
# media upload
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_returns_absolute_url(client):
    files = {"file": ("photo.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 64), "image/png")}
    res = await client.post("/api/v1/media/upload", files=files)
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["url"].startswith("http")
    assert body["url"].endswith(body["filename"])
    assert body["size_bytes"] > 0


@pytest.mark.asyncio
async def test_upload_rejects_disallowed_extension(client):
    files = {"file": ("payload.exe", io.BytesIO(b"MZ"), "application/octet-stream")}
    assert (await client.post("/api/v1/media/upload", files=files)).status_code == 400


@pytest.mark.asyncio
async def test_upload_cannot_escape_the_upload_directory(client):
    """A traversal name used to write outside ./uploads because the extension
    check passed and the uuid prefix did not neutralise the '../'."""
    from app.utils.storage import ensure_upload_dir_exists

    upload_dir = ensure_upload_dir_exists()
    escaped = os.path.abspath(os.path.join(upload_dir, "..", "pwned.png"))
    assert not os.path.exists(escaped)

    files = {"file": ("../../pwned.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")}
    res = await client.post("/api/v1/media/upload", files=files)

    assert res.status_code == 201
    written = os.path.join(upload_dir, res.json()["filename"])
    assert os.path.commonpath([upload_dir, os.path.abspath(written)]) == upload_dir
    assert not os.path.exists(escaped), "upload escaped the upload directory"
    os.remove(written)
