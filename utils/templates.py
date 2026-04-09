"""Shared Jinja2 environment with app-wide filters."""
from fastapi.templating import Jinja2Templates

from utils.display_date import format_display_date


def get_templates() -> Jinja2Templates:
    t = Jinja2Templates(directory="templates")
    t.env.filters["display_date"] = format_display_date
    return t
