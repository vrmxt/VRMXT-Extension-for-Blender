# SPDX-License-Identifier: MIT
from types import SimpleNamespace
from unittest import TestCase

from io_scene_vrmxt.common.constants import EXTENSION_MATERIALS_MTOONXT
from io_scene_vrmxt.mtoonxt.shadows import (
    export_shadows,
    import_shadows,
    set_shadow_adapter,
)


class ShadowReceivers(TestCase):
    def test_material_identity_and_independent_controls(self):
        face, hair, accessory = object(), object(), object()
        mapping = {0: hair, 1: accessory, 2: face}
        gltf = {
            "materials": [{"extensions": {"VRMC_materials_mtoon": {}}} for _ in mapping]
        }
        context = SimpleNamespace(material_index_to_material=mapping, json_dict=gltf)
        out = {}
        self.addCleanup(set_shadow_adapter)
        for others, own in ((False, False), (False, True), (True, False), (True, True)):
            rules = {face: (others, own, [hair, hair, face, object()])}
            set_shadow_adapter(
                lambda m, rules=rules: rules.get(m, (True, True, [])),
                lambda m, o, s, c: out.update({m: (o, s, c)}),
            )
            export_shadows(context)
            (row,) = gltf["extensions"][EXTENSION_MATERIALS_MTOONXT]["shadowReceivers"]
            self.assertEqual(
                row,
                dict(
                    receiver=2,
                    receiveOthers=others,
                    receiveSelf=own,
                    excludedCasters=[0],
                ),
            )
            out.clear()
            import_shadows(context)
            self.assertEqual(out, {face: (others, own, [hair])})
        set_shadow_adapter(lambda m: (True, True, []))
        export_shadows(context)
        self.assertNotIn("extensions", gltf)
