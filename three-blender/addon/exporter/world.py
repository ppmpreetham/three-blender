from pathlib import Path
import shutil

import bpy

from .colors import to_hex


class WorldExporter:
    def __init__(self, state):
        self._state = state

    def generate(self) -> str:
        world = bpy.context.scene.world
        lines = ["// World settings carried over from Blender"]
        env_url = self._export_environment(world)
        if env_url:
            loader = "EXRLoader" if self._state.env_is_exr else "RGBELoader"
            lines.append(f"// The Blender HDRI becomes both the backdrop and image-based lighting")
            lines.append(
                f"new {loader}().load('{env_url}', (texture) => {{"
            )
            lines.append("  texture.mapping = THREE.EquirectangularReflectionMapping;")
            lines.append("  scene.environment = texture;")
            lines.append("  scene.background = texture;")
            lines.append("});")
        else:
            background = to_hex(world.color) if world else "0x000000"
            self._state.background_hex = background
            lines.append(f"scene.background = new THREE.Color({background});")
        lines.extend(self._fog_lines(world))
        return "\n".join(lines) + "\n"

    def _fog_lines(self, world) -> list[str]:
        if not (world and world.mist_settings.use_mist):
            return []
        mist = world.mist_settings
        start = mist.start
        end = mist.start + mist.depth
        color = self._state.background_hex
        return [
            f"// Distance haze matching the Blender mist pass ({mist.falloff.lower()} falloff approximated as linear)",
            f"scene.fog = new THREE.Fog({color}, {start:.6g}, {end:.6g});",
        ]

    def _export_environment(self, world):
        image = self._environment_image(world)
        if image is None:
            return None
        source = Path(bpy.path.abspath(image.filepath_raw or ""))
        if not source.exists() and image.packed_file:
            try:
                image.save()
            except RuntimeError:
                return None
            source = Path(bpy.path.abspath(image.filepath_raw or ""))
        if not source.exists():
            return None
        extension = source.suffix.lower()
        destination = self._state.paths.textures_dir / f"{self._state.sanitizer.file_name(image.name)}{extension}"
        shutil.copyfile(source, destination)
        self._state.env_is_exr = extension == ".exr"
        self._state.env_texture_url = f"textures/{destination.name}"
        return self._state.env_texture_url

    @staticmethod
    def _environment_image(world):
        if not (world and world.use_nodes and world.node_tree):
            return None
        for node in world.node_tree.nodes:
            if node.type == "TEX_ENVIRONMENT" and node.image is not None:
                return node.image
        return None
