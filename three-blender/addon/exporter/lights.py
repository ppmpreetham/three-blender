import bpy
from mathutils import Vector

from .colors import to_hex
from .coords import position, quaternion

TRACK_CONSTRAINTS = {"TRACK_TO", "DAMPED_TRACK", "LOCKED_TRACK"}
SHADOW_MAP_SIZE = 1024
SUN_SHADOW_MAP_SIZE = 2048
SUN_SHADOW_EXTENT = 15.0
SUN_SHADOW_FAR = 60.0


class LightExporter:
    def __init__(self, state):
        self._state = state

    def generate(self) -> str:
        lights = [obj for obj in bpy.data.objects if obj.type == "LIGHT"]
        lines = ["// Lights recreated from Blender lamps (power values come straight from Blender)"]
        for obj in lights:
            emitter = getattr(self, f"_emit_{obj.data.type.lower()}", None)
            if emitter is not None:
                lines.extend(emitter(obj))
        return "\n".join(lines) + "\n"

    def _name_for(self, obj) -> str:
        return self._state.sanitizer.sanitize(obj.name)

    def _emit_point(self, obj) -> list[str]:
        light = obj.data
        name = self._name_for(obj)
        lines = [
            f"// Point light '{obj.name}': omni-directional with Blender's falloff and range",
            (
                f"const {name} = new THREE.PointLight({to_hex(light.color)}, "
                f"{light.energy:.6g}, {light.cutoff_distance:.6g}, 2.0);"
            ),
            f"{name}.position.set({position(obj.matrix_world.translation)});",
        ]
        if light.use_shadow:
            self._state.shadow_lights = True
            radius = max(light.shadow_soft_size, 0.001)
            lines.extend(
                [
                    f"{name}.castShadow = true;",
                    f"{name}.shadow.mapSize.set({SHADOW_MAP_SIZE}, {SHADOW_MAP_SIZE});",
                    f"{name}.shadow.bias = -0.0005;",
                    f"{name}.shadow.radius = {radius:.6g};",
                ]
            )
        lines.append(f"scene.add({name});")
        lines.append("")
        return lines

    def _emit_spot(self, obj) -> list[str]:
        light = obj.data
        name = self._name_for(obj)
        target = self._target_position(obj)
        lines = [
            f"// Spot light '{obj.name}': cone angle, soft edge and range from the Blender lamp",
            (
                f"const {name} = new THREE.SpotLight({to_hex(light.color)}, {light.energy:.6g}, "
                f"{light.cutoff_distance:.6g}, {light.spot_size:.6f}, {light.spot_blend:.6f}, 2.0);"
            ),
            f"{name}.position.set({position(obj.matrix_world.translation)});",
            f"{name}.target.position.set({position(target)});",
        ]
        if light.use_shadow:
            self._state.shadow_lights = True
            lines.extend(
                [
                    f"{name}.castShadow = true;",
                    f"{name}.shadow.mapSize.set({SHADOW_MAP_SIZE}, {SHADOW_MAP_SIZE});",
                    f"{name}.shadow.bias = -0.0005;",
                ]
            )
        lines.append(f"scene.add({name});")
        lines.append(f"scene.add({name}.target);")
        lines.append("")
        return lines

    def _emit_sun(self, obj) -> list[str]:
        light = obj.data
        name = self._name_for(obj)
        origin = obj.matrix_world.translation
        target = origin + obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))
        lines = [
            f"// Sun light '{obj.name}': parallel rays shining along the lamp's -Z axis",
            f"const {name} = new THREE.DirectionalLight({to_hex(light.color)}, {light.energy:.6g});",
            f"{name}.position.set({position(origin)});",
            f"{name}.target.position.set({position(target)});",
        ]
        if light.use_shadow:
            self._state.shadow_lights = True
            extent = SUN_SHADOW_EXTENT * max(1.0, light.energy**0.5)
            lines.extend(
                [
                    f"{name}.castShadow = true;",
                    f"{name}.shadow.mapSize.set({SUN_SHADOW_MAP_SIZE}, {SUN_SHADOW_MAP_SIZE});",
                    f"{name}.shadow.camera.left = {-extent:.6g};",
                    f"{name}.shadow.camera.right = {extent:.6g};",
                    f"{name}.shadow.camera.top = {extent:.6g};",
                    f"{name}.shadow.camera.bottom = {-extent:.6g};",
                    f"{name}.shadow.camera.far = {SUN_SHADOW_FAR:.6g};",
                    f"{name}.shadow.bias = -0.0005;",
                ]
            )
        lines.append(f"scene.add({name});")
        lines.append(f"scene.add({name}.target);")
        lines.append("")
        return lines

    def _emit_area(self, obj) -> list[str]:
        light = obj.data
        name = self._name_for(obj)
        width, height = _area_dimensions(light)
        self._state.rect_area = True
        return [
            f"// Area light '{obj.name}' ({width:g} x {height:g}): a real rectangular emitter; three.js cannot shadow it",
            (
                f"const {name} = new THREE.RectAreaLight({to_hex(light.color)}, "
                f"{light.energy:.6g}, {width:.6g}, {height:.6g});"
            ),
            f"{name}.position.set({position(obj.matrix_world.translation)});",
            f"{name}.quaternion.set({quaternion(obj.matrix_world.to_3x3())});",
            f"scene.add({name});",
            "",
        ]

    def _target_position(self, obj) -> Vector:
        for constraint in obj.constraints:
            if constraint.type in TRACK_CONSTRAINTS and constraint.target is not None:
                return constraint.target.matrix_world.translation.copy()
        return obj.matrix_world.translation + obj.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))


def _area_dimensions(light) -> tuple[float, float]:
    if light.shape in {"RECTANGLE", "ELLIPSE"}:
        return light.size, light.size_y
    return light.size, light.size
