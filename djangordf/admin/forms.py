"""Auto-generated Django forms for ``RDFModel`` classes.

Property-to-form-field mapping:

* ``DataProperty(datatype=XSD.string)`` (or no datatype) → ``CharField``
* ``DataProperty(datatype=XSD.integer)`` → ``IntegerField``
* ``DataProperty(datatype=XSD.boolean)`` → ``BooleanField``
* ``DataProperty(datatype=XSD.float)`` → ``FloatField``
* ``DataProperty(datatype=XSD.dateTime)`` → ``DateTimeField``
* ``LangStringProperty`` → ``CharField`` with ``value@lang`` text shape
* ``URIProperty`` → ``URLField``
* ``ObjectProperty`` → ``CharField`` taking the target's IRI verbatim
* ``many=True`` on any of the above → ``CharField`` rendered as a
  ``Textarea``, one value per non-empty line

``required=`` on the property propagates to the form field.
"""
from typing import Dict

from django import forms
from rdflib import URIRef
from rdflib.namespace import XSD

from ..namespaces import LangString
from ..properties import (
    DataProperty,
    LangStringProperty,
    ObjectProperty,
    URIProperty,
)


def _build_scalar_field(prop) -> forms.Field:
    if isinstance(prop, URIProperty):
        return forms.URLField(required=prop.required)
    if isinstance(prop, ObjectProperty):
        return forms.CharField(required=prop.required)
    if isinstance(prop, LangStringProperty):
        return forms.CharField(
            required=prop.required,
            help_text="Use the 'value@lang' shape, e.g. 'Buch@de'.",
        )
    if isinstance(prop, DataProperty):
        datatype = prop.datatype
        if datatype == XSD.integer:
            return forms.IntegerField(required=prop.required)
        if datatype == XSD.boolean:
            return forms.BooleanField(required=prop.required)
        if datatype == XSD.float or datatype == XSD.double:
            return forms.FloatField(required=prop.required)
        if datatype == XSD.dateTime:
            return forms.DateTimeField(required=prop.required)
        return forms.CharField(required=prop.required)
    return forms.CharField(required=prop.required)


def _build_many_field(prop) -> forms.Field:
    return forms.CharField(
        required=prop.required,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text="One value per line.",
    )


def _value_to_initial(prop, value):
    """Convert the Python value stored on an instance to the textual
    form the field expects as ``initial``."""
    if value is None:
        return ""
    if isinstance(prop, LangStringProperty):
        if prop.many:
            return "\n".join(f"{ls.value}@{ls.lang}" for ls in value)
        return f"{value.value}@{value.lang}"
    if isinstance(prop, ObjectProperty):
        if prop.many:
            return "\n".join(str(_iri_of(v)) for v in value)
        return str(_iri_of(value))
    if isinstance(prop, URIProperty):
        if prop.many:
            return "\n".join(str(v) for v in value)
        return str(value)
    if isinstance(prop, DataProperty):
        if prop.many:
            return "\n".join(str(v) for v in value)
        if prop.datatype == XSD.boolean:
            return bool(value)
        return value
    return str(value)


def _iri_of(value):
    if isinstance(value, URIRef):
        return value
    if hasattr(value, "iri") and value.iri is not None:
        return URIRef(value.iri)
    return URIRef(str(value))


def _parse_langstring(text: str) -> LangString:
    if "@" not in text:
        raise forms.ValidationError(
            "LangString must be in 'value@lang' form."
        )
    value, lang = text.rsplit("@", 1)
    return LangString(value, lang)


def _coerce_many(prop, raw: str):
    """Parse a Textarea body of one-value-per-line into a list of
    Python values matching ``prop``'s scalar semantics."""
    if not raw or not raw.strip():
        return []
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    return [_coerce_scalar(prop, line) for line in lines]


def _coerce_scalar(prop, value):
    """Map a single cleaned form value to the Python value that
    ``prop`` expects on the model instance."""
    if isinstance(prop, LangStringProperty):
        if not isinstance(value, str):
            value = str(value)
        return _parse_langstring(value)
    if isinstance(prop, ObjectProperty):
        return prop.target_class(iri=URIRef(str(value)))
    if isinstance(prop, URIProperty):
        return URIRef(str(value))
    if isinstance(prop, DataProperty):
        if prop.datatype == XSD.boolean:
            return bool(value)
        if prop.datatype == XSD.integer:
            return int(value)
        if prop.datatype == XSD.float or prop.datatype == XSD.double:
            return float(value)
        # datetime + string both keep the cleaned value as-is.
        return value
    return value


def _field_names(model_class, only=None) -> Dict[str, object]:
    """Pick property names from the model class, optionally filtered."""
    if only is None:
        return dict(model_class._properties)
    return {
        name: model_class._properties[name]
        for name in only
        if name in model_class._properties
    }


def build_form_class(
    model_class,
    *,
    fields=None,
) -> type:
    """Construct a Django ``forms.Form`` subclass with one field per
    declared property of ``model_class``. ``fields`` optionally
    restricts the field set, in order."""
    attrs: Dict[str, object] = {}
    selected = _field_names(model_class, only=fields)
    for name, prop in selected.items():
        if prop.predicate is None:
            continue
        if getattr(prop, "reverse", False):
            continue
        if prop.many:
            field = _build_many_field(prop)
        else:
            field = _build_scalar_field(prop)
        field.label = name.replace("_", " ").title()
        attrs[name] = field

    def _init(self, *args, instance=None, **kwargs):
        self._instance = instance
        if instance is not None and "initial" not in kwargs:
            initial = {}
            for name, prop in selected.items():
                if prop.predicate is None:
                    continue
                if getattr(prop, "reverse", False):
                    continue
                initial[name] = _value_to_initial(
                    prop, getattr(instance, name, None),
                )
            kwargs["initial"] = initial
        forms.Form.__init__(self, *args, **kwargs)

    def _clean(self):
        """Run Django's standard clean and then layer the property-
        specific coercions on top. ``LangString`` parsing in particular
        must happen here (rather than in ``_kwargs_for_save``) so its
        errors surface during ``is_valid()``."""
        cleaned = forms.Form.clean(self) or self.cleaned_data
        for name, prop in selected.items():
            if prop.predicate is None or getattr(prop, "reverse", False):
                continue
            raw = cleaned.get(name)
            try:
                if prop.many:
                    cleaned[name] = _coerce_many(prop, raw or "")
                elif raw in (None, ""):
                    cleaned[name] = None
                else:
                    cleaned[name] = _coerce_scalar(prop, raw)
            except forms.ValidationError as exc:
                self.add_error(name, exc)
        return cleaned

    def _kwargs_for_save(self) -> Dict[str, object]:
        return {
            name: self.cleaned_data.get(name)
            for name in selected
            if selected[name].predicate is not None
            and not getattr(selected[name], "reverse", False)
        }

    def _save(self):
        """Persist the form-bound instance. Builds a new one when no
        ``instance`` was passed; otherwise updates the bound one."""
        manager = model_class.objects
        kwargs = self._kwargs_for_save()
        if self._instance is None:
            return manager.create(**kwargs)
        for name, value in kwargs.items():
            setattr(self._instance, name, value)
        self._instance.save()
        return self._instance

    attrs["__init__"] = _init
    attrs["clean"] = _clean
    attrs["_kwargs_for_save"] = _kwargs_for_save
    attrs["save"] = _save
    attrs["_rdf_model_class"] = model_class
    attrs["_selected_properties"] = selected

    return type(
        f"{model_class.__name__}Form",
        (forms.Form,),
        attrs,
    )


class RDFModelForm(forms.Form):
    """Marker base class so callers can isinstance-check generated
    forms. Real forms are constructed by :func:`build_form_class`
    and inherit from ``forms.Form`` (not this class) — type stays
    available for static-typing purposes only."""

    @classmethod
    def for_model(cls, model_class, *, fields=None) -> type:
        return build_form_class(model_class, fields=fields)
