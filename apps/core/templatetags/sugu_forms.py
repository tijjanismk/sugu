"""Rendu des champs de formulaire avec les classes du design (composant FormField)."""

from django import template

register = template.Library()


def _aria_attrs(bound_field) -> dict:
    attrs = {}
    described_by = []
    if bound_field.help_text:
        described_by.append(f"{bound_field.auto_id}_help")
    if bound_field.errors:
        described_by.append(f"{bound_field.auto_id}_error")
        attrs["aria-invalid"] = "true"
    if described_by:
        attrs["aria-describedby"] = " ".join(described_by)
    return attrs


@register.filter
def sg_widget(bound_field):
    """Rend le widget avec `sg-input` et relie l'aide et l'erreur par aria-describedby."""
    attrs = _aria_attrs(bound_field)
    if bound_field.widget_type not in ("checkbox", "radioselect", "checkboxselectmultiple"):
        attrs["class"] = "sg-input"
    return bound_field.as_widget(attrs=attrs)


@register.filter
def sg_widget_bare(bound_field):
    """Widget sans `sg-input`, pour un champ à suffixe : le cadre est porté par le parent."""
    return bound_field.as_widget(attrs=_aria_attrs(bound_field))
