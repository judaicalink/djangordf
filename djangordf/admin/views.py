"""Function-based views powering :class:`RDFAdminSite`."""
from urllib.parse import quote

from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse


def _admin_for(site, model_name):
    try:
        return site.get_admin(model_name)
    except KeyError as exc:
        raise Http404(
            f"No RDFModelAdmin registered for {model_name!r}"
        ) from exc


def index(request, *, site):
    return render(
        request,
        "djangordf/admin/index.html",
        {"site": site, "registered": site.registered()},
    )


def changelist_view(request, model_name, *, site):
    admin = _admin_for(site, model_name)
    qs = list(admin.get_queryset())
    columns = list(admin.list_columns())
    rows = []
    for instance in qs:
        iri = str(instance.iri) if instance.iri is not None else ""
        cells = [admin.render_list_cell(instance, col) for col in columns]
        rows.append({
            "iri": iri,
            "iri_quoted": quote(iri, safe=""),
            "cells": cells,
        })
    return render(
        request,
        "djangordf/admin/changelist.html",
        {
            "site": site,
            "admin": admin,
            "model_name": model_name,
            "columns": columns,
            "rows": rows,
            "add_url": reverse(
                "djangordf_admin:add", kwargs={"model_name": model_name},
            ),
        },
    )


def add_view(request, model_name, *, site):
    admin = _admin_for(site, model_name)
    form_cls = admin.get_form_class()
    if request.method == "POST":
        form = form_cls(request.POST)
        if form.is_valid():
            form.save()
            return redirect(
                reverse(
                    "djangordf_admin:changelist",
                    kwargs={"model_name": model_name},
                )
            )
    else:
        form = form_cls()
    return render(
        request,
        "djangordf/admin/change_form.html",
        {
            "site": site,
            "admin": admin,
            "model_name": model_name,
            "form": form,
            "is_add": True,
        },
    )


def change_view(request, model_name, iri, *, site):
    admin = _admin_for(site, model_name)
    try:
        instance = admin.get_object(iri)
    except admin.model_class.DoesNotExist as exc:
        raise Http404(str(exc))

    form_cls = admin.get_form_class()
    if request.method == "POST":
        form = form_cls(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            return redirect(
                reverse(
                    "djangordf_admin:changelist",
                    kwargs={"model_name": model_name},
                )
            )
    else:
        form = form_cls(instance=instance)
    return render(
        request,
        "djangordf/admin/change_form.html",
        {
            "site": site,
            "admin": admin,
            "model_name": model_name,
            "form": form,
            "instance": instance,
            "is_add": False,
        },
    )


def delete_view(request, model_name, iri, *, site):
    admin = _admin_for(site, model_name)
    try:
        instance = admin.get_object(iri)
    except admin.model_class.DoesNotExist as exc:
        raise Http404(str(exc))
    if request.method == "POST":
        instance.delete()
        return redirect(
            reverse(
                "djangordf_admin:changelist",
                kwargs={"model_name": model_name},
            )
        )
    return render(
        request,
        "djangordf/admin/delete_confirm.html",
        {
            "site": site,
            "admin": admin,
            "model_name": model_name,
            "instance": instance,
        },
    )
