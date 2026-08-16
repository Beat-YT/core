"""Tests for the Hydro-Québec Peak Events binary sensors."""

from unittest.mock import MagicMock

from freezegun.api import FrozenDateTimeFactory

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant

from . import setup_integration

from tests.common import MockConfigEntry, async_fire_time_changed

ENTITY_PREFIX = "binary_sensor.credit_hivernal_residentiel_cpc_d"


async def test_day_flags(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Today/tomorrow flags reflect the local-day schedule."""
    # 2026-01-09 12:00 EST: AM+PM events today, AM event tomorrow
    freezer.move_to("2026-01-09T17:00:00+00:00")
    await setup_integration(hass, mock_config_entry)

    expected = {
        f"{ENTITY_PREFIX}_peak_event_in_progress": STATE_OFF,
        f"{ENTITY_PREFIX}_peak_event_today_am": STATE_ON,
        f"{ENTITY_PREFIX}_peak_event_today_pm": STATE_ON,
        f"{ENTITY_PREFIX}_peak_event_tomorrow_am": STATE_ON,
        f"{ENTITY_PREFIX}_peak_event_tomorrow_pm": STATE_OFF,
    }
    for entity_id, expected_state in expected.items():
        state = hass.states.get(entity_id)
        assert state is not None, entity_id
        assert state.state == expected_state, entity_id


async def test_peak_active_during_event(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The in-progress flag is on during an event."""
    # 17:00 EST: inside the 16:00-20:00 EST event
    freezer.move_to("2026-01-09T22:00:00+00:00")
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(f"{ENTITY_PREFIX}_peak_event_in_progress")
    assert state is not None
    assert state.state == STATE_ON


async def test_peak_active_flips_at_boundary(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    mock_client: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The in-progress flag flips at the event boundary, not the next poll."""
    # 15:59 EST, one minute before the 16:00-20:00 EST event
    freezer.move_to("2026-01-09T20:59:00+00:00")
    await setup_integration(hass, mock_config_entry)

    state = hass.states.get(f"{ENTITY_PREFIX}_peak_event_in_progress")
    assert state is not None
    assert state.state == STATE_OFF

    # Cross the event start; the coordinator's boundary timer must fire
    freezer.move_to("2026-01-09T21:00:01+00:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    state = hass.states.get(f"{ENTITY_PREFIX}_peak_event_in_progress")
    assert state is not None
    assert state.state == STATE_ON
