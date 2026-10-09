# -*- coding: utf-8 -*-
"""Пакує файли для сторінки 3D-перегляду (сервіс сторінок не віддає .glb/.hdr — кладемо їх base64-текстом):
    blender -b ../zmiy_logistic.blend --python pack_viewer.py
→ zmiy_logistic_glb.txt  — модель (GLB з JPEG-текстурами, легший за робочий PNG-GLB; лише для перегляду)
→ sky_hdri.txt           — HDRI для реалістичного освітлення (Kloofendal 48d Partly Cloudy, Poly Haven, CC0)
Концепти надбудови (Top_A/B/C) додає ../concepts/superstructure.py — він сам викликає pack() з ними.
Потім опублікувати zmiy_viewer.html разом із цими двома файлами (див. README.md поруч)."""
import base64
import os
import sys
import tempfile

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import zmiy_export as ze     # noqa: E402


def pack(extra=()):
    tmp = os.path.join(tempfile.mkdtemp(prefix="zmiy_view_"), "view.glb")
    ze.select(ze.BASE + list(extra))
    swaps = ze._downscaled_copies(2048)          # для перегляду досить 2048 (корпус у файлах — 4096)
    try:
        _export(tmp)
    finally:
        ze._restore(swaps)
    _write(tmp)


def _export(tmp):
    bpy.ops.export_scene.gltf(filepath=tmp, export_format='GLB', use_selection=True, export_apply=True,
                              export_yup=True, export_texcoords=True, export_normals=True,
                              export_materials='EXPORT', export_image_format='JPEG', export_jpeg_quality=90,
                              export_extras=False)


def _write(tmp):
    for src, dst in ((tmp, "zmiy_logistic_glb.txt"),
                     (os.path.join(HERE, "sky_kloofendal_48d_partly_cloudy_1k.hdr"), "sky_hdri.txt")):
        data = open(src, "rb").read()
        with open(os.path.join(HERE, dst), "w") as f:
            f.write(base64.b64encode(data).decode())
        print("[viewer] %s: %.1f MB → %s" % (os.path.basename(src), len(data) / 1e6, dst))


if __name__ == "__main__":
    pack([o.name for o in bpy.data.objects if o.name.startswith("Top_")])
