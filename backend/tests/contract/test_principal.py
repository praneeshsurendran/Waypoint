import pytest
from pydantic import ValidationError
from waypoint_security import Principal


def test_verified_principal_requires_an_explicit_active_account_and_known_role():
    profile = {
        "id": 1,
        "username": "one",
        "full_name": "One",
        "role": "DRIVER",
        "is_active": True,
    }
    assert Principal.model_validate(profile).role == "DRIVER"
    for invalid in (
        {**profile, "role": "UNKNOWN"},
        {**profile, "is_active": False},
        {key: value for key, value in profile.items() if key != "is_active"},
    ):
        with pytest.raises(ValidationError):
            Principal.model_validate(invalid)
