"""Tests for ``djangordf.admin`` — form generation, views, and routing."""
import pytest
from rdflib import URIRef
from rdflib.namespace import XSD


@pytest.fixture
def in_memory_backend(settings):
    settings.DJANGORDF_BACKEND = {
        "class": "djangordf.backends.memory.InMemoryBackend",
    }
    settings.DJANGORDF_DEFAULT_NAMESPACE = "http://example.org/d/"
    settings.DJANGORDF_DEFAULT_GRAPH = "http://example.org/g"


def _admin_term_model(name):
    from djangordf import (
        DataProperty,
        LangStringProperty,
        ObjectProperty,
        RDFModel,
        URIProperty,
    )

    Term = type(
        name,
        (RDFModel,),
        {
            "title": DataProperty(
                predicate=URIRef("http://example.org/title"),
            ),
            "count": DataProperty(
                predicate=URIRef("http://example.org/count"),
                datatype=XSD.integer,
            ),
            "homepage": URIProperty(
                predicate=URIRef("http://example.org/hp"),
            ),
            "pref_label": LangStringProperty(),
            "broader": ObjectProperty(
                "self",
                predicate=URIRef("http://example.org/broader"),
            ),
            "tags": DataProperty(
                predicate=URIRef("http://example.org/tag"),
                many=True,
            ),
        },
    )
    return Term


# -- form generation --------------------------------------------------------

def test_build_form_class_maps_dataproperty_string_to_charfield():
    from django import forms
    from djangordf.admin.forms import build_form_class

    Term = _admin_term_model("AdmFormCharStr")
    FormCls = build_form_class(Term)
    field = FormCls.base_fields["title"]
    assert isinstance(field, forms.CharField)


def test_build_form_class_maps_dataproperty_integer_to_integerfield():
    from django import forms
    from djangordf.admin.forms import build_form_class

    Term = _admin_term_model("AdmFormInt")
    FormCls = build_form_class(Term)
    field = FormCls.base_fields["count"]
    assert isinstance(field, forms.IntegerField)


def test_build_form_class_maps_uriproperty_to_urlfield():
    from django import forms
    from djangordf.admin.forms import build_form_class

    Term = _admin_term_model("AdmFormUrl")
    FormCls = build_form_class(Term)
    field = FormCls.base_fields["homepage"]
    assert isinstance(field, forms.URLField)


def test_build_form_class_many_uses_textarea():
    from django import forms
    from djangordf.admin.forms import build_form_class

    Term = _admin_term_model("AdmFormMany")
    FormCls = build_form_class(Term)
    field = FormCls.base_fields["tags"]
    assert isinstance(field.widget, forms.Textarea)


def test_form_save_creates_new_instance(in_memory_backend):
    from djangordf.admin.forms import build_form_class

    Term = _admin_term_model("AdmFormSaveCreate")
    FormCls = build_form_class(Term)
    form = FormCls(data={
        "title": "Hello",
        "count": "5",
        "homepage": "http://example.org/page",
        "pref_label": "Welt@de",
        "broader": "http://example.org/d/p1",
        "tags": "a\nb\nc",
    })
    assert form.is_valid(), form.errors
    inst = form.save()
    assert inst.title == "Hello"
    assert inst.count == 5
    assert inst.homepage == URIRef("http://example.org/page")
    assert inst.pref_label.value == "Welt"
    assert inst.pref_label.lang == "de"
    assert inst.broader.iri == URIRef("http://example.org/d/p1")
    assert inst.tags == ["a", "b", "c"]


def test_form_save_updates_existing_instance(in_memory_backend):
    from djangordf.admin.forms import build_form_class

    Term = _admin_term_model("AdmFormSaveUpdate")
    inst = Term.objects.create(title="old")
    FormCls = build_form_class(Term)
    form = FormCls(data={"title": "new"}, instance=inst)
    assert form.is_valid(), form.errors
    form.save()
    reloaded = Term.objects.get(inst.iri)
    assert reloaded.title == "new"


def test_form_initial_value_for_existing_instance(in_memory_backend):
    from djangordf.admin.forms import build_form_class
    from djangordf.namespaces import LangString

    Term = _admin_term_model("AdmFormInitial")
    inst = Term.objects.create(
        title="t", count=7, pref_label=LangString("x", "en"),
    )
    FormCls = build_form_class(Term)
    form = FormCls(instance=inst)
    assert form.initial["title"] == "t"
    assert form.initial["count"] == 7
    assert form.initial["pref_label"] == "x@en"


def test_form_langstring_validation_rejects_missing_lang(in_memory_backend):
    from djangordf.admin.forms import build_form_class

    Term = _admin_term_model("AdmFormLangBad")
    FormCls = build_form_class(Term)
    form = FormCls(data={"pref_label": "no-at-here"})
    assert not form.is_valid()
    assert "pref_label" in form.errors


# -- site registration -----------------------------------------------------

def test_rdf_admin_site_register_decorator_form():
    from djangordf.admin import (
        RDFAdminSite, RDFModelAdmin,
    )
    from djangordf import RDFModel

    class AdmRegTarget(RDFModel):
        pass

    site = RDFAdminSite()

    @site.register(AdmRegTarget)
    class AdmRegAdmin(RDFModelAdmin):
        list_display = ("iri",)

    assert site.is_registered(AdmRegTarget)
    assert isinstance(site.get_admin("AdmRegTarget"), AdmRegAdmin)


def test_rdf_admin_site_register_two_arg_form():
    from djangordf.admin import RDFAdminSite, RDFModelAdmin
    from djangordf import RDFModel

    class AdmRegTwo(RDFModel):
        pass

    site = RDFAdminSite()
    site.register(AdmRegTwo, RDFModelAdmin)
    assert site.is_registered(AdmRegTwo)


# -- end-to-end views via Django test client -------------------------------

@pytest.fixture
def client():
    from django.test import Client
    return Client(enforce_csrf_checks=False)


def test_index_view_lists_registered_models(client, in_memory_backend):
    from djangordf import RDFModel
    from djangordf.admin import rdf_admin_site

    class AdmIndexed(RDFModel):
        pass

    rdf_admin_site.register(AdmIndexed)
    try:
        response = client.get("/admin/rdf/")
        assert response.status_code == 200
        assert b"AdmIndexed" in response.content
    finally:
        rdf_admin_site.unregister(AdmIndexed)


def test_changelist_view_renders_instances(client, in_memory_backend):
    from djangordf.admin import rdf_admin_site

    Term = _admin_term_model("AdmChangeList")
    Term.objects.create(title="A")
    Term.objects.create(title="B")

    rdf_admin_site.register(Term)
    try:
        response = client.get(f"/admin/rdf/{Term.__name__}/")
        assert response.status_code == 200
        # iri column appears in the body for both rows.
        body = response.content.decode("utf-8")
        assert body.count("example.org/d/") >= 2
    finally:
        rdf_admin_site.unregister(Term)


def test_add_view_creates_instance(client, in_memory_backend):
    from djangordf.admin import rdf_admin_site

    Term = _admin_term_model("AdmAdd")
    rdf_admin_site.register(Term)
    try:
        response = client.post(
            f"/admin/rdf/{Term.__name__}/add/",
            data={
                "title": "via-admin",
                "count": "11",
                "homepage": "http://example.org/h",
                "pref_label": "X@en",
                "broader": "http://example.org/d/anchor",
                "tags": "one\ntwo",
            },
        )
        assert response.status_code == 302
        all_titles = sorted(t.title for t in Term.objects.all())
        assert "via-admin" in all_titles
    finally:
        rdf_admin_site.unregister(Term)


def test_change_view_updates_instance(client, in_memory_backend):
    from djangordf.admin import rdf_admin_site
    from urllib.parse import quote

    Term = _admin_term_model("AdmChange")
    inst = Term.objects.create(title="before")
    rdf_admin_site.register(Term)
    try:
        url = (
            f"/admin/rdf/{Term.__name__}/"
            f"{quote(str(inst.iri), safe='')}/"
        )
        response = client.post(url, data={"title": "after"})
        assert response.status_code == 302
        reloaded = Term.objects.get(inst.iri)
        assert reloaded.title == "after"
    finally:
        rdf_admin_site.unregister(Term)


def test_delete_view_removes_instance(client, in_memory_backend):
    from djangordf.admin import rdf_admin_site
    from urllib.parse import quote

    Term = _admin_term_model("AdmDelete")
    inst = Term.objects.create(title="goodbye")
    rdf_admin_site.register(Term)
    try:
        url = (
            f"/admin/rdf/{Term.__name__}/"
            f"{quote(str(inst.iri), safe='')}/delete/"
        )
        response = client.post(url)
        assert response.status_code == 302
        with pytest.raises(Term.DoesNotExist):
            Term.objects.get(inst.iri)
    finally:
        rdf_admin_site.unregister(Term)


def test_change_view_404s_unknown_iri(client, in_memory_backend):
    from djangordf.admin import rdf_admin_site
    from urllib.parse import quote

    Term = _admin_term_model("AdmChange404")
    rdf_admin_site.register(Term)
    try:
        url = (
            f"/admin/rdf/{Term.__name__}/"
            f"{quote('http://example.org/d/no-such', safe='')}/"
        )
        response = client.get(url)
        assert response.status_code == 404
    finally:
        rdf_admin_site.unregister(Term)


def test_changelist_view_404s_unregistered_model(client, in_memory_backend):
    response = client.get("/admin/rdf/NotRegisteredModel/")
    assert response.status_code == 404


# -- importable ------------------------------------------------------------

def test_public_admin_classes_are_importable_from_package_root():
    from djangordf.admin import (
        RDFAdminSite,
        RDFModelAdmin,
        RDFModelForm,
        rdf_admin_site,
    )
    assert isinstance(rdf_admin_site, RDFAdminSite)
    assert callable(RDFModelAdmin)
    assert callable(RDFModelForm)
