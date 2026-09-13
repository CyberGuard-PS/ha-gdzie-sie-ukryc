"""Configuration from the HA UI, including multiple existing zones."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import validate_url
from .const import DEFAULTS, DOMAIN, MAX_ZONES, NAME, settings


def schema(values):
    return vol.Schema(
        {
            vol.Required("source_mode", default=values["source_mode"]): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "psp", "label": "Automatycznie z gdziesieukryc.pl"},
                        {"value": "import", "label": "Import JSON w karcie mapy"},
                        {"value": "file", "label": "Lokalny plik JSON / GeoJSON"},
                        {"value": "url", "label": "Jawny adres feedu JSON (zaawansowane)"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Required("zones", default=values["zones"]): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="zone", multiple=True)
            ),
            vol.Required("radius_km", default=values["radius_km"]): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0.5, max=50, step=0.5, unit_of_measurement="km", mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required("max_routes", default=values["max_routes"]): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=10)
            ),
            vol.Required("candidate_limit", default=values["candidate_limit"]): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=30)
            ),
            vol.Required("update_hours", default=values["update_hours"]): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=168)
            ),
            vol.Required("routing_url", default=values["routing_url"]): selector.TextSelector(),
            vol.Optional("data_file", default=values["data_file"]): selector.TextSelector(),
            vol.Optional("feed_url", default=values["feed_url"]): selector.TextSelector(),
        }
    )


def validate(values):
    errors = {}
    zones = list(dict.fromkeys(values.get("zones", [])))
    if not zones or len(zones) > MAX_ZONES or any(not x.startswith("zone.") for x in zones):
        errors["zones"] = "invalid_zones"
    values["zones"] = zones
    if values["candidate_limit"] < values["max_routes"]:
        errors["candidate_limit"] = "too_few_candidates"
    try:
        values["routing_url"] = validate_url(values["routing_url"])
    except ValueError:
        errors["routing_url"] = "invalid_url"
    if values["source_mode"] == "url":
        try:
            values["feed_url"] = validate_url(values.get("feed_url", ""))
        except ValueError:
            errors["feed_url"] = "invalid_url"
    if values["source_mode"] == "file" and not values.get("data_file", "").strip():
        errors["data_file"] = "invalid_file"
    return errors


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        errors = validate(user_input) if user_input else {}
        if user_input is not None and not errors:
            return self.async_create_entry(title=NAME, data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=schema({**DEFAULTS, **(user_input or {})}), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlow()


class OptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        errors = validate(user_input) if user_input else {}
        if user_input is not None and not errors:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init", data_schema=schema({**settings(self.config_entry), **(user_input or {})}), errors=errors
        )
