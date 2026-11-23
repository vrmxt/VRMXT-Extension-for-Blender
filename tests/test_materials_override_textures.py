# SPDX-License-Identifier: MIT
"""Tests for materials-override texture import bind + export remap."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest import mock

from io_scene_vrmxt.materials_override.export_hook import (
    apply_materials_override_export,
)
from io_scene_vrmxt.materials_override.import_hook import bind_override_texture_images


class TestBindOverrideTextureImages(unittest.TestCase):
    def test_binds_image_from_texture_index(self) -> None:
        image = object()
        item = SimpleNamespace(
            prop_type="texture",
            texture_index=0,
            image=None,
        )
        slot = SimpleNamespace(properties=[item])
        settings = SimpleNamespace(authored=True, overrides=[slot])
        material = SimpleNamespace(vrmxt_materials_override_settings=settings)

        bound = bind_override_texture_images(
            material,
            {"textures": [{"source": 3}]},
            {3: image},
        )
        self.assertEqual(bound, 1)
        self.assertIs(item.image, image)

    def test_skips_when_image_already_set(self) -> None:
        existing = object()
        item = SimpleNamespace(
            prop_type="texture",
            texture_index=0,
            image=existing,
        )
        slot = SimpleNamespace(properties=[item])
        settings = SimpleNamespace(authored=True, overrides=[slot])
        material = SimpleNamespace(vrmxt_materials_override_settings=settings)

        bound = bind_override_texture_images(
            material,
            {"textures": [{"source": 3}]},
            {3: object()},
        )
        self.assertEqual(bound, 0)
        self.assertIs(item.image, existing)


class TestRemapTexturePropertiesForExport(unittest.TestCase):
    def export(self, properties):
        def slot(shader, props):
            return SimpleNamespace(
                engine="unity",
                material_id=shader,
                variant="builtin",
                id_type="shaderName",
                properties=props,
            )

        settings = SimpleNamespace(
            authored=True,
            overrides=[
                slot(
                    "",
                    [
                        SimpleNamespace(
                            name="_MainTex", prop_type="texture", image=object()
                        )
                    ],
                ),
                slot("Standard", properties),
            ],
        )
        material = SimpleNamespace(
            name="Coat", vrmxt_materials_override_settings=settings
        )
        base = {"baseColorTexture": {"index": 3, "texCoord": 1}}
        gltf = {"name": "Coat", "pbrMetallicRoughness": base.copy()}
        context = SimpleNamespace(
            json_dict={"materials": [gltf]},
            buffer0=bytearray(),
            image_name_to_index={},
            material_name_to_index={"Coat": 0},
            material_index_to_material={0: material},
        )
        apply_materials_override_export(context)
        self.assertEqual(gltf["pbrMetallicRoughness"], base)
        (entry,) = gltf["extensions"]["VRMXT_materials_override"]["overrides"]
        return entry["properties"]

    @mock.patch(
        "io_scene_vrmxt.materials_override.export_hook.ensure_vfx_texture_index",
        return_value=0,
    )
    def test_explicit_image_survives_filtered_slots_and_properties(self, pack):
        image = object()
        output = self.export(
            [
                SimpleNamespace(name="", prop_type="texture", image=object()),
                SimpleNamespace(name="_Color", prop_type="vector"),
                SimpleNamespace(
                    name="_MainTex", prop_type="texture", image=image, texture_index=24
                ),
            ]
        )
        self.assertEqual(
            output[-1], {"name": "_MainTex", "type": "texture", "texture": 0}
        )
        self.assertEqual(len(output), 2)
        pack.assert_called_once()
        self.assertIs(pack.call_args.kwargs["image"], image)

    @mock.patch(
        "io_scene_vrmxt.materials_override.export_hook.ensure_vfx_texture_index"
    )
    def test_parameter_only_preserves_original_texture(self, pack):
        scalar = SimpleNamespace(
            name="_Glossiness", prop_type="scalar", value_float=0.25
        )
        expected = [{"name": "_Glossiness", "type": "scalar", "value": 0.25}]
        self.assertEqual(self.export([scalar]), expected)
        stale = SimpleNamespace(
            name="_MainTex", prop_type="texture", image=None, texture_index=24
        )
        self.assertEqual(self.export([stale, scalar]), expected)
        pack.assert_not_called()


if __name__ == "__main__":
    unittest.main()
