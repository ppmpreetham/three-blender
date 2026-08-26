import tempfile
from pathlib import Path

import bpy

BAKE_RESOLUTION = 1024
CHECKED_INPUTS = ("Base Color", "Roughness", "Metallic", "Normal", "Emission Color")
SRGB = "sRGB"
NON_COLOR = "Non-Color"


def _safe_file_name(name: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in name)


class MaterialBaker:
    def __init__(self, resolution: int = BAKE_RESOLUTION):
        self._resolution = resolution
        self._baked = {}
        self._temp_dir = Path(tempfile.mkdtemp(prefix="three_blender_bake_"))

    def prepare(self, obj) -> list:
        swaps = []
        for slot in obj.material_slots:
            material = slot.material
            if material is None or not material.use_nodes:
                continue
            if material.name not in self._baked:
                self._baked[material.name] = self._bake(material, obj)
            replacement = self._baked[material.name]
            if replacement is not None:
                swaps.append((slot, material))
                slot.material = replacement
        return swaps

    @staticmethod
    def restore(swaps: list) -> None:
        for slot, original in reversed(swaps):
            slot.material = original

    def _bake(self, original, obj):
        principled = self._principled(original)
        if principled is None:
            return None
        linked = tuple(name for name in CHECKED_INPUTS if self._linked(principled, name))
        if not linked:
            return None
        self._ensure_uv(obj)
        scene = bpy.context.scene
        previous_engine = scene.render.engine
        scene.render.engine = "CYCLES"
        scene.cycles.samples = 1
        scene.cycles.use_denoising = False
        try:
            images = self._bake_channels(principled, obj, original)
        finally:
            scene.render.engine = previous_engine
        if not images:
            return None
        return self._assemble(original, principled, images)

    def _bake_channels(self, principled, obj, material) -> dict:
        images = {}
        if self._linked(principled, "Emission Color"):
            images["Emission Color"] = self._bake_pass(obj, material, "EMIT", colorspace=SRGB)
        if self._linked(principled, "Base Color"):
            images["Base Color"] = self._bake_pass(
                obj, material, "DIFFUSE", pass_filter={"COLOR"}, colorspace=SRGB
            )
        if self._linked(principled, "Normal"):
            images["Normal"] = self._bake_pass(obj, material, "NORMAL")
        if self._linked(principled, "Roughness"):
            images["Roughness"] = self._bake_value(obj, material, self._driver(principled, "Roughness"))
        if self._linked(principled, "Metallic"):
            images["Metallic"] = self._bake_value(obj, material, self._driver(principled, "Metallic"))
        return images

    def _bake_pass(self, obj, material, bake_type: str, pass_filter=None, colorspace: str = NON_COLOR):
        image = self._new_image(f"{material.name}_{bake_type}", colorspace)
        target = material.node_tree.nodes.new("ShaderNodeTexImage")
        target.image = image
        material.node_tree.nodes.active = target
        self._select(obj)
        kwargs = {"type": bake_type, "use_clear": True, "margin": 4}
        if pass_filter:
            kwargs["pass_filter"] = pass_filter
        bpy.ops.object.bake(**kwargs)
        return self._persist(image)

    def _bake_value(self, obj, material, source_socket):
        tree = material.node_tree
        emission = tree.nodes.new("ShaderNodeEmission")
        output = next(node for node in tree.nodes if node.type == "OUTPUT_MATERIAL")
        previous = output.inputs["Surface"].links[0].from_socket if output.inputs["Surface"].is_linked else None
        tree.links.new(source_socket, emission.inputs["Color"])
        tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
        try:
            return self._bake_pass(obj, material, "EMIT")
        finally:
            for link in list(output.inputs["Surface"].links):
                tree.links.remove(link)
            if previous is not None:
                tree.links.new(previous, output.inputs["Surface"])
            tree.nodes.remove(emission)

    def _assemble(self, original, principled, images: dict):
        export_material = original.copy()
        tree = export_material.node_tree
        tree.nodes.clear()
        output = tree.nodes.new("ShaderNodeOutputMaterial")
        shader = tree.nodes.new("ShaderNodeBsdfPrincipled")
        tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        for source_input in principled.inputs:
            target = shader.inputs.get(source_input.name)
            if target is None or source_input.is_linked:
                continue
            if not hasattr(source_input, "default_value"):
                continue
            try:
                target.default_value = source_input.default_value
            except (TypeError, ValueError):
                continue
        for socket_name, image in images.items():
            texture = tree.nodes.new("ShaderNodeTexImage")
            texture.image = image
            texture.location = (-400.0, 0.0)
            if socket_name == "Normal":
                normal_map = tree.nodes.new("ShaderNodeNormalMap")
                normal_map.inputs["Strength"].default_value = 1.0
                tree.links.new(texture.outputs["Color"], normal_map.inputs["Color"])
                tree.links.new(normal_map.outputs["Normal"], shader.inputs["Normal"])
            else:
                tree.links.new(texture.outputs["Color"], shader.inputs[socket_name])
        if "Emission Color" in images and "Emission Strength" in shader.inputs:
            shader.inputs["Emission Strength"].default_value = 1.0
        return export_material

    @staticmethod
    def _principled(material):
        return next(
            (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
            None,
        )

    @staticmethod
    def _linked(principled, name: str) -> bool:
        return name in principled.inputs and principled.inputs[name].is_linked

    @staticmethod
    def _driver(principled, name: str):
        return principled.inputs[name].links[0].from_socket

    @staticmethod
    def _select(obj) -> None:
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

    @staticmethod
    def _ensure_uv(obj) -> None:
        if obj.data.uv_layers:
            return
        MaterialBaker._select(obj)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project()
        bpy.ops.object.mode_set(mode="OBJECT")

    def _new_image(self, name: str, colorspace: str):
        image = bpy.data.images.new(name, self._resolution, self._resolution, alpha=False)
        image.colorspace_settings.name = colorspace
        return image

    def _persist(self, image):
        path = self._temp_dir / f"{_safe_file_name(image.name)}.png"
        image.filepath_raw = str(path)
        image.file_format = "PNG"
        image.save()
        persisted = bpy.data.images.load(str(path), check_existing=False)
        persisted.name = image.name
        return persisted
