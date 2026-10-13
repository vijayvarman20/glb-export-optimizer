# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Vijay Varman
#
# GLB Export Optimizer is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

bl_info = {
    "name": "GLB Export Optimizer",
    "author": "Vijay Varman",
    "version": (1, 1, 0),
    "blender": (5, 0, 0),
    "location": "File Browser > Export Options",
    "description": "Export selected objects to GLB with Draco compression and file-size comparison",
    "category": "Import-Export",
}

import os
import tempfile
import bpy
from bpy.props import BoolProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper


def _gltf_operator():
    operator = getattr(bpy.ops.export_scene, "gltf", None)
    if operator is None:
        raise RuntimeError(
            "Blender's glTF exporter is unavailable. Enable the built-in "
            "'glTF 2.0 format' exporter and try again."
        )
    return operator


def _operator_properties(operator):
    try:
        return operator.get_rna_type().properties
    except Exception:
        return None


def _format_bytes(byte_count):
    size = float(byte_count)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0 or unit == "TB":
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} TB"


def _run_gltf_export(filepath, draco_enabled, compression_level,
                      position_quantization, normal_quantization,
                      texcoord_quantization, color_quantization,
                      generic_quantization):
    """Call Blender's built-in exporter and explicitly pass supported settings."""
    operator = _gltf_operator()
    props = _operator_properties(operator)

    kwargs = {
        "filepath": filepath,
        "export_format": "GLB",
        "use_selection": True,
        "export_draco_mesh_compression_enable": bool(draco_enabled),
        "export_draco_mesh_compression_level": int(compression_level),
        "export_draco_position_quantization": int(position_quantization),
        "export_draco_normal_quantization": int(normal_quantization),
        "export_draco_texcoord_quantization": int(texcoord_quantization),
        "export_draco_color_quantization": int(color_quantization),
        "export_draco_generic_quantization": int(generic_quantization),
    }

    if props is not None:
        valid_names = {prop.identifier for prop in props}
        if draco_enabled and "export_draco_mesh_compression_enable" not in valid_names:
            raise RuntimeError(
                "The active glTF exporter does not expose Draco compression. "
                "Enable/update Blender's built-in glTF 2.0 exporter."
            )
        kwargs = {key: value for key, value in kwargs.items() if key in valid_names}

    # Print actual settings passed to the built-in exporter to make debugging easy.
    print(
        "[GLB Export Optimizer] Export settings:",
        {k: v for k, v in kwargs.items() if "draco" in k}
    )
    result = operator("EXEC_DEFAULT", **kwargs)
    if "FINISHED" not in result:
        raise RuntimeError("Blender's glTF exporter did not finish successfully.")
    if not os.path.isfile(filepath):
        raise RuntimeError("The glTF exporter finished but no output file was found.")


class GLEO_OT_export_glb(bpy.types.Operator, ExportHelper):
    """Export selected objects to GLB using the options shown in this file browser."""
    bl_idname = "gleo.export_glb"
    bl_label = "Export Optimized GLB"
    bl_options = {"REGISTER"}

    filename_ext = ".glb"
    filter_glob: StringProperty(default="*.glb", options={"HIDDEN"})
    check_existing: BoolProperty(default=True, options={"HIDDEN"})

    draco_enabled: BoolProperty(
        name="Enable Draco Compression",
        description="Compress supported mesh geometry using KHR_draco_mesh_compression",
        default=True,
    )
    compression_level: IntProperty(
        name="Compression Level",
        description="0 prioritizes speed; 6 prioritizes compression. Values above 6 are not supported by the exporter",
        default=6,
        min=0,
        max=6,
    )
    compare_file_sizes: BoolProperty(
        name="Compare File Sizes",
        description="Export a temporary uncompressed comparison file and report the actual size difference",
        default=True,
    )
    position_quantization: IntProperty(
        name="Position Quantization",
        description="Quantization bits for positions; lower values can reduce size but may reduce precision",
        default=14, min=0, max=30,
    )
    normal_quantization: IntProperty(
        name="Normal Quantization",
        description="Quantization bits for normals",
        default=10, min=0, max=30,
    )
    texcoord_quantization: IntProperty(
        name="UV Quantization",
        description="Quantization bits for texture coordinates",
        default=12, min=0, max=30,
    )
    color_quantization: IntProperty(
        name="Color Quantization",
        description="Quantization bits for vertex colors",
        default=10, min=0, max=30,
    )
    generic_quantization: IntProperty(
        name="Generic Quantization",
        description="Quantization bits for generic attributes",
        default=12, min=0, max=30,
    )

    def invoke(self, context, event):
        if not context.selected_objects:
            self.report({"ERROR"}, "Select one or more objects before exporting.")
            return {"CANCELLED"}
        # ExportHelper opens Blender's native file browser. The custom panel below
        # displays this operator's properties in the right-hand Options region.
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        if not context.selected_objects:
            self.report({"ERROR"}, "Select one or more objects before exporting.")
            return {"CANCELLED"}

        output_path = bpy.path.abspath(self.filepath)
        if not output_path.lower().endswith(".glb"):
            output_path += ".glb"
        output_path = os.path.abspath(output_path)
        output_dir = os.path.dirname(output_path)
        if not output_dir or not os.path.isdir(output_dir):
            self.report({"ERROR"}, "Choose an existing output folder.")
            return {"CANCELLED"}

        # Snapshot current selection references. The operator does not edit scene data.
        selected = list(context.selected_objects)
        temp_path = None
        try:
            uncompressed_size = None
            if self.draco_enabled and self.compare_file_sizes:
                fd, temp_path = tempfile.mkstemp(
                    prefix=".gleo_uncompressed_", suffix=".glb", dir=output_dir
                )
                os.close(fd)
                os.remove(temp_path)
                _run_gltf_export(
                    temp_path, False, self.compression_level,
                    self.position_quantization, self.normal_quantization,
                    self.texcoord_quantization, self.color_quantization,
                    self.generic_quantization,
                )
                uncompressed_size = os.path.getsize(temp_path)

            _run_gltf_export(
                output_path, self.draco_enabled, self.compression_level,
                self.position_quantization, self.normal_quantization,
                self.texcoord_quantization, self.color_quantization,
                self.generic_quantization,
            )
            final_size = os.path.getsize(output_path)

            if uncompressed_size is not None:
                delta = uncompressed_size - final_size
                pct = delta / uncompressed_size * 100.0 if uncompressed_size else 0.0
                if delta >= 0:
                    message = (
                        f"Exported {_format_bytes(final_size)}; uncompressed "
                        f"{_format_bytes(uncompressed_size)}; saved "
                        f"{_format_bytes(delta)} ({pct:.1f}%)."
                    )
                else:
                    message = (
                        f"Exported {_format_bytes(final_size)}; Draco output is "
                        f"{_format_bytes(-delta)} larger ({abs(pct):.1f}%)."
                    )
            else:
                message = f"Exported {_format_bytes(final_size)}."
                message += " Draco enabled." if self.draco_enabled else " Draco disabled."

            self.report({"INFO"}, message)
            print("[GLB Export Optimizer] " + message)
        except Exception as exc:
            self.report({"ERROR"}, f"GLB export failed: {exc}")
            return {"CANCELLED"}
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    print("[GLB Export Optimizer] Warning: temporary file cleanup failed.")

        return {"FINISHED"}


class GLEO_PT_filebrowser_options(bpy.types.Panel):
    bl_space_type = "FILE_BROWSER"
    bl_region_type = "TOOL_PROPS"
    bl_label = "GLB Export Optimizer"
    bl_idname = "GLEO_PT_filebrowser_options"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        space = context.space_data
        operator = getattr(space, "active_operator", None) if space else None
        return operator is not None and operator.bl_idname == "GLEO_OT_export_glb"

    def draw(self, context):
        layout = self.layout
        operator = context.space_data.active_operator
        layout.use_property_split = True
        layout.use_property_decorate = False

        layout.label(text="Export Settings", icon="EXPORT")
        layout.prop(operator, "draco_enabled")
        col = layout.column()
        col.enabled = operator.draco_enabled
        col.prop(operator, "compression_level")
        quant_box = col.box()
        quant_box.label(text="Quantization")
        quant_box.prop(operator, "position_quantization")
        quant_box.prop(operator, "normal_quantization")
        quant_box.prop(operator, "texcoord_quantization")
        quant_box.prop(operator, "color_quantization")
        quant_box.prop(operator, "generic_quantization")
        layout.separator()
        layout.prop(operator, "compare_file_sizes")
        layout.label(text="Scope: selected objects only", icon="RESTRICT_SELECT_OFF")
        layout.label(text="Output: GLB", icon="FILE")


CLASSES = (
    GLEO_OT_export_glb,
    GLEO_PT_filebrowser_options,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
