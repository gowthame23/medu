import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_family_group_lifecycle_and_guards(client: AsyncClient, create_user_fixture):
    admin_user, admin_token = await create_user_fixture("admin@family.com", "Admin Alice")
    member_user, member_token = await create_user_fixture("member@family.com", "Member Bob")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # 1. Admin creates group
    create_res = await client.post(
        "/api/v1/families",
        json={"group_name": "The Alice Family", "timezone": "Asia/Kolkata"},
        headers=admin_headers
    )
    assert create_res.status_code == 201
    group = create_res.json()
    group_id = group["id"]
    assert group["group_name"] == "The Alice Family"
    assert group["my_role"] == "ADMIN"

    # 2. Admin invites member
    invite_res = await client.post(
        f"/api/v1/families/{group_id}/invitations",
        json={"email": "member@family.com"},
        headers=admin_headers
    )
    assert invite_res.status_code == 201
    invitation = invite_res.json()
    assert "invite_token" in invitation
    raw_invite_token = invitation["invite_token"]

    # 3. Member accepts invitation
    accept_res = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_invite_token},
        headers=member_headers
    )
    assert accept_res.status_code == 200
    assert accept_res.json()["my_role"] == "MEMBER"

    # 4. Token reuse fails
    reuse_res = await client.post(
        "/api/v1/invitations/accept",
        json={"token": raw_invite_token},
        headers=member_headers
    )
    assert reuse_res.status_code == 409

    # 5. Last Admin Guard: Admin attempts to leave or demote herself -> 409 Conflict
    leave_res = await client.post(
        f"/api/v1/families/{group_id}/leave",
        headers=admin_headers
    )
    assert leave_res.status_code == 409
    assert "sole admin" in leave_res.json()["error"]["message"]

    demote_res = await client.patch(
        f"/api/v1/families/{group_id}/members/{admin_user.id}",
        json={"role": "MEMBER"},
        headers=admin_headers
    )
    assert demote_res.status_code == 409
    assert "last remaining admin" in demote_res.json()["error"]["message"]
