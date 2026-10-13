"""Rendu des champs de formulaire avec les classes du design (composant FormField)."""

from django import template

register = template.Library()


@register.filter
def sg_widget(bound_field):
    """Rend le widget avec `sg-input` et relie l'aide et l'erreur par aria-describedby."""
    attrs = {}
    if bound_field.widget_type not in ("checkbox", "radioselect", "checkboxselectmultiple"):
        attrs["class"] = "sg-input"
    described_by = []
    if bound_field.help_text:
        described_by.append(f"{bound_field.auto_id}_help")
    if bound_field.errors:
        described_by.append(f"{bound_field.auto_id}_error")
        attrs["aria-invalid"] = "true"
    if described_by:
        attrs["aria-describedby"] = " ".join(described_by)
    return bound_field.as_widget(attrs=attrs)
