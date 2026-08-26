import bpy

TONE_MAPPING_MODE_BY_VIEW_TRANSFORM = {
    "AgX": "AGX",
    "Filmic": "ACES_FILMIC",
    "Khronos PBR Neutral": "NEUTRAL",
}


class PostFXExporter:
    def __init__(self, state, camera_object, scene):
        self._state = state
        self._camera = camera_object
        self._scene = scene

    def generate(self) -> str:
        if not self._state.post_processing:
            return ""
        lines = [
            "// Post-processing: WebGL-grade antialiasing plus the effects found in your Blender file",
            "const composer = new EffectComposer(renderer, { frameBufferType: THREE.HalfFloatType });",
            "composer.addPass(new RenderPass(scene, activeCamera));",
            "const effects = [new SMAAEffect({ preset: SMAAPreset.MEDIUM })];",
        ]
        lines.extend(self._bloom_lines())
        lines.extend(self._dof_lines())
        lines.extend(self._tone_mapping_lines())
        lines.append("composer.addPass(new EffectPass(activeCamera, ...effects));")
        return "\n".join(lines) + "\n"

    def _bloom_lines(self) -> list[str]:
        glare = self._glare_node()
        if glare is None:
            return []
        threshold = max(self._node_param(glare, "Threshold", 1.0), 0.0)
        smoothing = min(max(self._node_param(glare, "Smoothness", 0.2), 0.0), 1.0)
        self._state.fx_bloom = True
        return [
            f"// Bloom taken from the compositor Glare node (threshold {threshold:g})",
            (
                f"const bloom = new BloomEffect({{ luminanceThreshold: {threshold + 1.0:.4f}, "
                f"luminanceSmoothing: {smoothing:.4f}, intensity: 0.85, mipmapBlur: true }});"
            ),
            "effects.push(bloom);",
        ]

    @staticmethod
    def _node_param(node, name: str, fallback: float) -> float:
        if name in node.inputs:
            return float(node.inputs[name].default_value)
        return float(getattr(node, name.lower(), fallback))

    def _dof_lines(self) -> list[str]:
        data = self._camera.data if self._camera is not None else None
        dof = getattr(data, "dof", None)
        if dof is None or not dof.use_dof:
            return []
        far = max(data.clip_end, 0.001)
        focus_distance = min(max(dof.focus_distance / far, 0.0005), 1.0)
        focal_length = min(max((data.lens / 1000.0) / far, 0.0005), 1.0)
        bokeh_scale = min(max(16.0 / max(dof.aperture_fstop, 0.1), 1.0), 8.0)
        camera_name = self._state.sanitizer.sanitize(self._camera.name)
        self._state.fx_dof = True
        return [
            f"// Depth of field matching the Blender camera focus ({dof.focus_distance:g}m away)",
            (
                f"const depthOfField = new DepthOfFieldEffect({camera_name}, {{ "
                f"focusDistance: {focus_distance:.6f}, focalLength: {focal_length:.6f}, "
                f"bokehScale: {bokeh_scale:.6f}, height: 480 }});"
            ),
            "effects.push(depthOfField);",
        ]

    def _tone_mapping_lines(self) -> list[str]:
        view_transform = self._scene.view_settings.view_transform
        mode = TONE_MAPPING_MODE_BY_VIEW_TRANSFORM.get(view_transform)
        if mode is None:
            return []
        self._state.fx_tone_mapping = True
        return [
            f"// Tone mapping moved to the end of the chain to preserve '{view_transform}' colors",
            f"const toneMapping = new ToneMappingEffect({{ mode: ToneMappingMode.{mode} }});",
            "effects.push(toneMapping);",
        ]

    @staticmethod
    def _glare_node():
        tree = getattr(bpy.context.scene, "compositing_node_group", None)
        if tree is None:
            tree = getattr(bpy.context.scene, "node_tree", None)
        if tree is None:
            return None
        return next((node for node in tree.nodes if node.type == "GLARE"), None)
