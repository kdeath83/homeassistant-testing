"""Tests for the Lyngdorf media player platform."""

from unittest.mock import MagicMock

from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import (
    ATTR_ENTITY_ID,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_DOWN,
    SERVICE_VOLUME_MUTE,
    SERVICE_VOLUME_SET,
    SERVICE_VOLUME_UP,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def test_entities_created(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that both main zone and zone B entities are created."""
    assert init_integration.state.value == "loaded"

    # Check main zone entity exists
    main_zone = hass.states.get("media_player.mock_lyngdorf_main_zone")
    assert main_zone is not None
    assert main_zone.attributes["friendly_name"] == "Mock Lyngdorf Main Zone"

    # Check zone B entity exists
    zone_b = hass.states.get("media_player.mock_lyngdorf_zone_b")
    assert zone_b is not None
    assert zone_b.attributes["friendly_name"] == "Mock Lyngdorf Zone B"


async def test_entity_unique_ids(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
) -> None:
    """Test that entity unique IDs are set correctly."""
    entity_registry = er.async_get(hass)

    # Main zone unique ID
    main_zone = entity_registry.async_get("media_player.mock_lyngdorf_main_zone")
    assert main_zone is not None
    assert main_zone.unique_id == f"{init_integration.unique_id}_main_zone"

    # Zone B unique ID
    zone_b = entity_registry.async_get("media_player.mock_lyngdorf_zone_b")
    assert zone_b is not None
    assert zone_b.unique_id == f"{init_integration.unique_id}_zone_b"


async def test_main_zone_turn_on(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test turning on main zone."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "media_player.mock_lyngdorf_main_zone"},
        blocking=True,
    )

    assert mock_receiver.power_on is True


async def test_main_zone_turn_off(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test turning off main zone."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "media_player.mock_lyngdorf_main_zone"},
        blocking=True,
    )

    assert mock_receiver.power_on is False


async def test_zone_b_turn_on(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test turning on zone B."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_TURN_ON,
        {ATTR_ENTITY_ID: "media_player.mock_lyngdorf_zone_b"},
        blocking=True,
    )

    assert mock_receiver.zone_b_power_on is True


async def test_zone_b_turn_off(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test turning off zone B."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_TURN_OFF,
        {ATTR_ENTITY_ID: "media_player.mock_lyngdorf_zone_b"},
        blocking=True,
    )

    assert mock_receiver.zone_b_power_on is False


async def test_main_zone_volume_set(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test setting main zone volume."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_SET,
        {
            ATTR_ENTITY_ID: "media_player.mock_lyngdorf_main_zone",
            "volume_level": 0.5,
        },
        blocking=True,
    )

    # 0.5 * 100 - 80 = -30
    assert mock_receiver.volume == -30.0


async def test_zone_b_volume_set(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test setting zone B volume."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_SET,
        {
            ATTR_ENTITY_ID: "media_player.mock_lyngdorf_zone_b",
            "volume_level": 0.3,
        },
        blocking=True,
    )

    # 0.3 * 100 - 80 = -50
    assert mock_receiver.zone_b_volume == -50.0


async def test_main_zone_volume_up(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test volume up for main zone."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_UP,
        {ATTR_ENTITY_ID: "media_player.mock_lyngdorf_main_zone"},
        blocking=True,
    )

    mock_receiver.volume_up.assert_called_once()


async def test_main_zone_volume_down(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test volume down for main zone."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_DOWN,
        {ATTR_ENTITY_ID: "media_player.mock_lyngdorf_main_zone"},
        blocking=True,
    )

    mock_receiver.volume_down.assert_called_once()


async def test_zone_b_volume_up(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test volume up for zone B."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_UP,
        {ATTR_ENTITY_ID: "media_player.mock_lyngdorf_zone_b"},
        blocking=True,
    )

    mock_receiver.zone_b_volume_up.assert_called_once()


async def test_zone_b_volume_down(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test volume down for zone B."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_DOWN,
        {ATTR_ENTITY_ID: "media_player.mock_lyngdorf_zone_b"},
        blocking=True,
    )

    mock_receiver.zone_b_volume_down.assert_called_once()


async def test_main_zone_mute(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test muting main zone."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {
            ATTR_ENTITY_ID: "media_player.mock_lyngdorf_main_zone",
            "is_volume_muted": True,
        },
        blocking=True,
    )

    assert mock_receiver.mute_enabled is True


async def test_zone_b_mute(
    hass: HomeAssistant,
    init_integration: MockConfigEntry,
    mock_receiver: MagicMock,
) -> None:
    """Test muting zone B."""
    await hass.services.async_call(
        MEDIA_PLAYER_DOMAIN,
        SERVICE_VOLUME_MUTE,
        {
            ATTR_ENTITY_ID: "media_player.mock_lyngdorf_zone_b",
            "is_volume_muted": True,
        },
        blocking=True,
    )

    assert mock_receiver.zone_b_mute_enabled is True
