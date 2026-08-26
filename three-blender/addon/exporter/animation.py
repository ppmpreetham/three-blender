import bpy

from .coords import AXIS_CONVERSION


class TransformAnimator:
    def __init__(self, state):
        self._state = state

    def generate(self) -> str:
        scene = bpy.context.scene
        start = scene.frame_start
        end = scene.frame_end
        if end <= start:
            return ""
        fps = max(scene.render.fps, 1)
        blocks = []
        for obj in self._animated_objects():
            js_name = self._state.sanitizer.sanitize(obj.name)
            block = self._block_for(obj, js_name, start, end, fps)
            if block:
                self._state.has_object_animations = True
                blocks.append(block)
        return "\n".join(blocks) + "\n"

    @staticmethod
    def _animated_objects():
        for obj in bpy.data.objects:
            if obj.type not in {"CAMERA", "LIGHT"}:
                continue
            animation = obj.animation_data
            if animation and (animation.action or animation.drivers):
                yield obj

    def _block_for(self, obj, js_name: str, start: int, end: int, fps: int) -> str:
        times = []
        positions = []
        quaternions = []
        original_frame = bpy.context.scene.frame_current
        try:
            for frame in range(start, end + 1):
                bpy.context.scene.frame_set(frame)
                bpy.context.view_layer.update()
                matrix = obj.matrix_world
                rotation = AXIS_CONVERSION @ matrix.to_3x3() @ AXIS_CONVERSION.inverted()
                quaternion = rotation.to_quaternion()
                translation = matrix.translation
                times.append(f"{frame / fps:.5f}")
                positions.append(f"{translation.x:.5f}, {translation.z:.5f}, {-translation.y:.5f}")
                quaternions.append(
                    f"{quaternion.x:.5f}, {quaternion.y:.5f}, {quaternion.z:.5f}, {quaternion.w:.5f}"
                )
        finally:
            bpy.context.scene.frame_set(original_frame)
        duration = times[-1]
        return (
            f"// {obj.name} motion baked from Blender keyframes, constraints and drivers included\n"
            "{\n"
            f"  const clip = new THREE.AnimationClip('{js_name} Action', {duration}, [\n"
            f"    new THREE.VectorKeyframeTrack('.position', [{', '.join(times)}], [{', '.join(positions)}]),\n"
            f"    new THREE.QuaternionKeyframeTrack('.quaternion', [{', '.join(times)}], [{', '.join(quaternions)}]),\n"
            "  ]);\n"
            f"  const mixer = new THREE.AnimationMixer({js_name});\n"
            "  mixer.clipAction(clip).play();\n"
            "  mixers.push(mixer);\n"
            "}\n"
        )
