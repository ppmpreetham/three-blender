import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))

from addon.exporter import SceneExporter


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_mesh(name, location):
    bpy.ops.mesh.primitive_monkey_add()
    obj = bpy.context.active_object
    obj.name = name
    obj.location = location
    return obj


def add_procedural_material(obj):
    material = bpy.data.materials.new("Procedural Paint")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    noise = nodes.new("ShaderNodeTexNoise")
    color_ramp = nodes.new("ShaderNodeValToRGB")
    rough_ramp = nodes.new("ShaderNodeValToRGB")
    links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
    links.new(color_ramp.outputs["Color"], principled.inputs["Base Color"])
    links.new(noise.outputs["Fac"], rough_ramp.inputs["Fac"])
    links.new(rough_ramp.outputs["Color"], principled.inputs["Roughness"])
    obj.data.materials.append(material)


def add_shape_key(obj, name, offset):
    obj.shape_key_add(name="Basis")
    key = obj.shape_key_add(name=name)
    for vertex in key.data:
        vertex.co.z += offset
    return key


def build_scene():
    scene = bpy.context.scene
    cube = add_mesh("Cube A", (0.0, 0.0, 0.0))
    add_procedural_material(cube)
    add_shape_key(cube, "Wide", 0.35)

    linked = add_mesh("Cube B", (3.0, 0.0, 0.0))
    linked.data = cube.data

    child = add_mesh("Child Mesh", (1.0, 1.0, 1.0))
    child.parent = cube

    sphere = add_mesh("Animated Sphere", (-2.0, 2.0, 0.0))
    sphere.keyframe_insert(data_path="location", frame=1)
    sphere.location.z = 2.0
    sphere.keyframe_insert(data_path="location", frame=60)

    ghost = add_mesh("Ghost Cube", (-5.0, 0.0, 0.0))
    ghost.hide_render = True

    light_data = bpy.data.lights.new("Sun", type="SUN")
    light_data.energy = 3.0
    sun_obj = bpy.data.objects.new("Sun Lamp", light_data)
    sun_obj.rotation_euler = (0.9, 0.0, 0.7)
    scene.collection.objects.link(sun_obj)

    point_data = bpy.data.lights.new("Bulb", type="POINT")
    point_data.energy = 500.0
    point_data.shadow_soft_size = 0.25
    point_obj = bpy.data.objects.new("Bulb", point_data)
    point_obj.location = (2.0, -3.0, 4.0)
    scene.collection.objects.link(point_obj)

    spot_data = bpy.data.lights.new("Torch", type="SPOT")
    spot_data.energy = 800.0
    spot_data.spot_size = 0.6
    spot_data.spot_blend = 0.3
    spot_obj = bpy.data.objects.new("Torch", spot_data)
    spot_obj.location = (0.0, -6.0, 5.0)
    track = spot_obj.constraints.new(type="TRACK_TO")
    track.target = cube
    scene.collection.objects.link(spot_obj)

    area_data = bpy.data.lights.new("Panel", type="AREA")
    area_data.shape = "RECTANGLE"
    area_data.size = 2.0
    area_data.size_y = 4.0
    area_data.energy = 200.0
    area_obj = bpy.data.objects.new("Panel", area_data)
    area_obj.rotation_euler = (1.2, 0.0, 0.0)
    scene.collection.objects.link(area_obj)

    cam_data = bpy.data.cameras.new("Main Cam")
    cam_data.lens = 50.0
    cam_data.clip_start = 0.2
    cam_data.clip_end = 250.0
    cam_data.shift_x = 0.05
    cam_obj = bpy.data.objects.new("Main Cam", cam_data)
    cam_obj.location = (7.36, -6.93, 4.96)
    cam_obj.rotation_euler = (1.109, 0.0, 0.815)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj
    cam_obj.keyframe_insert(data_path="location", frame=1)
    cam_obj.location.x += 2.0
    cam_obj.keyframe_insert(data_path="location", frame=60)

    ortho_data = bpy.data.cameras.new("Top Ortho")
    ortho_data.type = "ORTHO"
    ortho_data.ortho_scale = 12.0
    ortho_obj = bpy.data.objects.new("Top Ortho", ortho_data)
    ortho_obj.location = (0.0, 0.0, 10.0)
    scene.collection.objects.link(ortho_obj)

    world = bpy.data.worlds.new("World")
    world.color = (0.05, 0.1, 0.2)
    world.mist_settings.use_mist = True
    world.mist_settings.start = 5.0
    world.mist_settings.depth = 40.0
    scene.world = world
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.exposure = 0.5
    return scene


def build_hdri_scene():
    reset_scene()
    scene = build_scene()
    hdr_source = Path(tempfile.mkdtemp(prefix="tb_hdr_src_")) / "studio.hdr"
    image = bpy.data.images.new("Studio Env", 64, 32)
    image.filepath_raw = str(hdr_source)
    image.file_format = "HDR"
    image.save()
    assert hdr_source.exists(), "test HDR asset failed to save"

    world = bpy.data.worlds.new("HDRI World")
    world.use_nodes = True
    nodes = world.node_tree.nodes
    nodes.clear()
    environment = nodes.new("ShaderNodeTexEnvironment")
    environment.image = bpy.data.images.load(str(hdr_source))
    background = nodes.new("ShaderNodeBackground")
    output = nodes.new("ShaderNodeOutputWorld")
    world.node_tree.links.new(environment.outputs["Color"], background.inputs["Color"])
    world.node_tree.links.new(background.outputs["Background"], output.inputs["Surface"])
    scene.world = world
    return scene


def export(scene):
    output_dir = Path(tempfile.mkdtemp(prefix="three_blender_smoke_"))
    html_file = SceneExporter(str(output_dir / "index.html"), scene=scene).run()
    assert html_file.exists(), "html missing"
    js_source = (output_dir / "script.js").read_text(encoding="utf-8")
    html_source = html_file.read_text(encoding="utf-8")
    models = sorted((output_dir / "models").glob("*.glb"))
    return output_dir, js_source, models, html_source


def build_postfx_scene():
    reset_scene()
    scene = build_scene()
    camera_data = scene.camera.data
    camera_data.dof.use_dof = True
    camera_data.dof.focus_distance = 12.0
    camera_data.dof.aperture_fstop = 2.8
    if getattr(scene, "compositing_node_group", "missing") == "missing":
        scene.node_tree = scene.node_tree or bpy.data.node_groups.new("ThreeBlenderCompositing", "CompositorNodeTree")
        tree = scene.node_tree
    else:
        if scene.compositing_node_group is None:
            scene.compositing_node_group = bpy.data.node_groups.new("ThreeBlenderCompositing", "CompositorNodeTree")
        tree = scene.compositing_node_group
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Bloom"
    glare.inputs["Threshold"].default_value = 0.9
    glare.inputs["Smoothness"].default_value = 0.4
    scene.threejs_use_postprocessing = True
    return scene


def check(js_source, models, output_dir, html_source):
    assert len(models) == 3, f"expected 3 unique mesh GLBs, got {[m.name for m in models]}"
    assert "Ghost_Cube" not in js_source, "render-hidden mesh must not be placed"
    assert js_source.count("placeModel('") == 4, "only render-visible instances are placed"
    expected_fov_prefix = "PerspectiveCamera(39.59"
    assert expected_fov_prefix in js_source, f"fov wrong: {[l for l in js_source.splitlines() if 'PerspectiveCamera(' in l]}"
    assert "OrthographicCamera" in js_source
    assert "DirectionalLight" in js_source, "sun lamp missing"
    assert "RectAreaLight" in js_source, "area lamp missing"
    assert "RectAreaLightUniformsLib.init()" in js_source
    assert "SpotLight" in js_source
    assert "new THREE.PointLight(0x" in js_source
    assert "AgXToneMapping" in js_source
    assert "scene.fog = new THREE.Fog(0x0d1a33, 5, 45);" in js_source
    assert "setViewOffset" in js_source
    assert "DRACOLoader" in js_source
    assert "placeModel('Cube_A'" in js_source and "placeModel('Cube_B'" in js_source
    assert "'models/suzanne.glb', [3" in js_source, "linked duplicate must reuse the first GLB"
    assert "mixers.forEach" in js_source
    assert "AnimationClip('Main_Cam Action'" in js_source, "camera keyframes missing"
    assert "QuaternionKeyframeTrack('.quaternion'" in js_source
    assert "new THREE.AnimationMixer(Main_Cam);" in js_source
    assert js_source.count("mixers.push(mixer);") >= 2, "camera mixer not registered"
    assert "activeCamera = Main_Cam;" in js_source
    camera_line = next(l for l in js_source.splitlines() if l.startswith("Main_Cam.position.set"))
    assert "9.36" in camera_line, f"camera position stale: {camera_line}"
    sun_target = next(l for l in js_source.splitlines() if "Sun_Lamp.target.position.set" in l)
    assert "-0.000000" not in sun_target and sun_target != SUN_IDENTITY_TARGET
    assert "postprocessing" not in js_source and "EffectComposer" not in js_source
    assert "postprocessing" not in html_source
    for name in ("index.html", "script.js"):
        assert (output_dir / name).exists()
    print(f"sizes: {[(m.name, m.stat().st_size) for m in models]}")


def check_hdri(output_dir, js_source):
    textures = sorted((output_dir / "textures").glob("*"))
    assert len(textures) == 1, f"expected one copied HDRI, got {textures}"
    expected_url = f"textures/{textures[0].name}"
    assert f"'{expected_url}'" in js_source, f"HDRI url missing: {expected_url}"
    assert "RGBELoader" in js_source
    assert "EquirectangularReflectionMapping" in js_source
    assert "scene.environment = texture;" in js_source
    assert "scene.background = texture;" in js_source


def syntax_check(output_dir):
    node = shutil.which("node")
    if not node:
        print("node not found; skipping JS syntax check")
        return
    target = output_dir / "script.mjs"
    shutil.copyfile(output_dir / "script.js", target)
    result = subprocess.run([node, "--check", str(target)], capture_output=True, text=True)
    assert result.returncode == 0, f"generated JS has syntax errors:\n{result.stderr}"
    target.unlink()


SUN_IDENTITY_TARGET = "Sun_Lamp.target.position.set(0.000000, -1.000000, 0.000000);"


def check_addon_lifecycle():
    import addon

    addon.register()
    addon.unregister()
    addon.register()
    assert bpy.types.Scene.threejs_html_path is not None
    assert bpy.types.Scene.threejs_use_postprocessing is not None
    print("addon register/unregister cycle OK")


def check_roundtrip(models):
    cube_glb = next(m for m in models if m.name == "suzanne.glb")
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(cube_glb))
    imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    assert imported, "round-trip import produced no meshes"
    has_image = any(
        node.type == "TEX_IMAGE"
        for obj in imported
        for slot in obj.material_slots
        if slot.material and slot.material.use_nodes
        for node in slot.material.node_tree.nodes
    )
    assert has_image, "procedural material was not baked into an embedded texture"
    with_keys = [obj for obj in imported if obj.data.shape_keys is not None]
    assert with_keys, "shape keys did not survive export"
    key_names = {key.name for key in with_keys[0].data.shape_keys.key_blocks}
    assert "Wide" in key_names, f"morph target missing: {key_names}"


def check_postfx(js_source, html_source):
    assert "postprocessing@6.39.4/build/index.js" in html_source
    assert "} from 'postprocessing';" in js_source
    assert "new EffectComposer(renderer, { frameBufferType: THREE.HalfFloatType });" in js_source
    assert "composer.addPass(new RenderPass(scene, activeCamera));" in js_source
    assert "new SMAAEffect({ preset: SMAAPreset.MEDIUM })" in js_source
    assert "BloomEffect({ luminanceThreshold: 1.9000" in js_source, "compositor glare threshold missing"
    assert "luminanceSmoothing: 0.4000" in js_source
    assert "DepthOfFieldEffect(Main_Cam," in js_source
    assert "ToneMappingMode.AGX" in js_source
    assert "renderer.toneMapping = THREE.NoToneMapping;" in js_source
    assert "composer.addPass(new EffectPass(activeCamera, ...effects));" in js_source
    assert "composer.setSize(window.innerWidth, window.innerHeight);" in js_source
    assert "composer.render(delta);" in js_source
    assert "mixers.forEach" in js_source


def main():
    check_addon_lifecycle()
    reset_scene()
    scene = build_scene()
    output_dir, js_source, models, html_source = export(scene)
    print(f"output in {output_dir}")
    check(js_source, models, output_dir, html_source)
    syntax_check(output_dir)
    check_roundtrip(models)

    postfx_scene = build_postfx_scene()
    postfx_dir, postfx_js, _, postfx_html = export(postfx_scene)
    check_postfx(postfx_js, postfx_html)
    syntax_check(postfx_dir)

    hdri_scene = build_hdri_scene()
    hdri_dir, hdri_js, _, _ = export(hdri_scene)
    check_hdri(hdri_dir, hdri_js)
    syntax_check(hdri_dir)
    print(f"PASS - output in {output_dir}")


if __name__ == "__main__":
    main()
