# SPDX-License-Identifier: MIT
"""Serialize Blender material override JSON into glTF material extensions."""

from __future__ import annotations

import logging
from typing import Any

from ..common.json_util import as_dict, as_list
from ..format.materials_override import (
    ensure_materials_override_extensions_used,
    write_raw_materials_override_to_material_dict,
)
from ..vfx.gltf_texture import ensure_vfx_texture_index
from .sync import read_extension_dict_for_export

logger = logging.getLogger(__name__)


def _texture_resolver(context: Any, material: Any):
    buffer0 = getattr(context, "buffer0", None)
    images = getattr(context, "image_name_to_index", None)
    if buffer0 is None or images is None:
        return None

    def resolve(item: Any) -> int | None:
        # Imported indices belong to the old glTF. Resolve each authored row
        # before serialization filters out incomplete slots and properties.
        image = getattr(item, "image", None)
        index = None
        if image is not None:
            index = ensure_vfx_texture_index(
                image=image,
                json_dict=context.json_dict,
                buffer0=buffer0,
                image_name_to_index=images,
            )
        if index is None:
            logger.warning(
                "VRMXT materials override: could not export texture %r on %r; "
                "assign a packable Blender Image",
                item.name,
                material.name,
            )
        return index

    return resolve


def apply_materials_override_export(context: Any) -> None:
    json_dict = context.json_dict
    materials_raw = as_list(json_dict.get("materials"))
    if materials_raw is None:
        return

    wrote_any = False
    material_index_to_material = dict(
        getattr(context, "material_index_to_material", {}) or {}
    )
    for material_name, material_index in context.material_name_to_index.items():
        material = material_index_to_material.get(material_index)
        if material is None:
            material = _find_material_by_name(material_name)
        if material is None:
            continue
        if material_index < 0 or material_index >= len(materials_raw):
            continue
        material_dict = as_dict(materials_raw[material_index])
        if material_dict is None:
            continue
        override_dict = read_extension_dict_for_export(
            material, _texture_resolver(context, material)
        )
        if override_dict is None:
            continue
        write_raw_materials_override_to_material_dict(material_dict, override_dict)
        wrote_any = True

    if wrote_any:
        ensure_materials_override_extensions_used(json_dict)


def _find_material_by_name(material_name: str) -> Any | None:
    try:
        import bpy
    except ImportError:
        return None
    for material in bpy.data.materials:
        if getattr(material, "name", None) == material_name:
            return material
    return None


def on_vrm1_export(context: Any) -> None:
    try:
        apply_materials_override_export(context)
    except Exception:  # noqa: BLE001 - hook must not abort stock VRM export
        logger.exception("VRMXT materials override export hook failed")


__all__ = ["apply_materials_override_export", "on_vrm1_export"]
