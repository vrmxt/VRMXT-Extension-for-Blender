# SPDX-License-Identifier: MIT
"""Material shadow policies use glTF indices at the file boundary."""

from __future__ import annotations

from ..common.constants import EXTENSION_MATERIALS_MTOONXT
from ..format.mtoonxt import ensure_mtoonxt_extensions_used, material_has_sibling_mtoon

_reader = _writer = None


def set_shadow_adapter(reader=None, writer=None):
    """Override RNA access with a reader and writer for (others, self, exclusions)."""
    global _reader, _writer
    _reader, _writer = reader, writer


def export_shadows(context):
    document = context.json_dict
    materials = document.get("materials", [])
    mapping = getattr(context, "material_index_to_material", {})
    indices = {
        material: index for index, material in mapping.items() if material is not None
    }
    rows = []
    for index, material in mapping.items():
        if (
            material is None
            or not 0 <= index < len(materials)
            or not material_has_sibling_mtoon(materials[index])
        ):
            continue
        if _reader:
            others, own, excluded = _reader(material)
        else:
            settings = getattr(material, "vrmxt_shadow_receiver", None)
            if settings is None:
                continue
            others, own = settings.receive_others, settings.receive_self
            excluded = (row.material for row in settings.excluded_casters)
        omit = sorted(
            {
                indices[caster]
                for caster in excluded
                if caster in indices and caster != material
            }
        )
        if omit or not (others and own):
            rows.append(
                dict(
                    receiver=index,
                    receiveOthers=others,
                    receiveSelf=own,
                    excludedCasters=omit,
                )
            )
    extensions = document.get("extensions", {})
    if rows:
        extension = document.setdefault("extensions", {}).setdefault(
            EXTENSION_MATERIALS_MTOONXT, {}
        )
        extension.update(specVersion="1.0", shadowReceivers=rows)
        ensure_mtoonxt_extensions_used(document)
    elif EXTENSION_MATERIALS_MTOONXT in extensions:
        extension = extensions[EXTENSION_MATERIALS_MTOONXT]
        extension.pop("shadowReceivers", None)
        if set(extension) <= {"specVersion"}:
            del extensions[EXTENSION_MATERIALS_MTOONXT]
            if not extensions:
                document.pop("extensions", None)


def import_shadows(context):
    document = context.json_dict
    ext = document.get("extensions", {}).get(EXTENSION_MATERIALS_MTOONXT, {})
    if not isinstance(ext, dict) or ext.get("specVersion") != "1.0":
        return
    rows = ext.get("shadowReceivers")
    if not isinstance(rows, list):
        return
    mapping = getattr(context, "material_index_to_material", {})
    materials = document.get("materials", [])
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        index = row.get("receiver")
        if (
            type(index) is not int
            or index in seen
            or index not in mapping
            or not 0 <= index < len(materials)
        ):
            continue
        mat = mapping[index]
        if mat is None or not material_has_sibling_mtoon(materials[index]):
            continue
        others, own = row.get("receiveOthers", True), row.get("receiveSelf", True)
        excluded = row.get("excludedCasters", [])
        if (
            type(others) is not bool
            or type(own) is not bool
            or not isinstance(excluded, list)
        ):
            continue
        seen.add(index)
        casters = list(
            dict.fromkeys(
                mapping[i]
                for i in excluded
                if type(i) is int and i != index and mapping.get(i) is not None
            )
        )
        if _writer:
            _writer(mat, others, own, casters)
        settings = getattr(mat, "vrmxt_shadow_receiver", None)
        if settings is not None:
            settings.receive_others, settings.receive_self = others, own
            settings.excluded_casters.clear()
            for caster in casters:
                settings.excluded_casters.add().material = caster
