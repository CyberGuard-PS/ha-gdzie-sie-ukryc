"""Authenticated geometry retrieval; import and forced refresh require HA admin."""

import json

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import callback

from .const import DOMAIN, MAX_BYTES
from .data import PayloadError


@callback
def async_register_commands(hass):
    for command in (websocket_list, websocket_data, websocket_import, websocket_refresh):
        websocket_api.async_register_command(hass, command)


def _coordinator(hass, msg):
    coordinator = hass.data.get(DOMAIN, {}).get(msg["entry_id"])
    if coordinator is None:
        raise PayloadError("Integracja nie jest załadowana")
    return coordinator


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/list"})
@websocket_api.async_response
async def websocket_list(hass, connection, msg):
    connection.send_result(
        msg["id"],
        [
            {"entry_id": entry_id, "title": coordinator.entry.title}
            for entry_id, coordinator in hass.data.get(DOMAIN, {}).items()
        ],
    )


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/data", vol.Required("entry_id"): str})
@websocket_api.async_response
async def websocket_data(hass, connection, msg):
    try:
        connection.send_result(msg["id"], _coordinator(hass, msg).export())
    except PayloadError as err:
        connection.send_error(msg["id"], "not_loaded", str(err))


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/import", vol.Required("entry_id"): str, vol.Required("payload"): dict}
)
@websocket_api.async_response
async def websocket_import(hass, connection, msg):
    connection.require_admin()
    try:
        if len(json.dumps(msg["payload"], ensure_ascii=False).encode("utf-8")) > MAX_BYTES:
            raise PayloadError("Import przekracza 8 MiB")
        result = await _coordinator(hass, msg).async_import(msg["payload"])
        connection.send_result(msg["id"], result)
    except (PayloadError, ValueError, TypeError) as err:
        connection.send_error(msg["id"], "import_failed", str(err))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/refresh", vol.Required("entry_id"): str})
@websocket_api.async_response
async def websocket_refresh(hass, connection, msg):
    connection.require_admin()
    try:
        coordinator = _coordinator(hass, msg)
        coordinator.force_routes = True
        await coordinator.async_refresh()
        connection.send_result(msg["id"], {"updated": True})
    except PayloadError as err:
        connection.send_error(msg["id"], "not_loaded", str(err))
