import bpy
from mathutils import Vector
from os import makedirs, path
from math import pi

blend_dir = bpy.path.abspath("//")
export_dir = path.join(blend_dir, "exported_gltfs")

# Dictionary to keep track of exported mesh data to avoid duplicate exports
exported_meshes = {}

def safe_js_name(name):
    """Sichert einen gültigen JavaScript Namen (z. B. für Objekte und Lichter)."""
    return name.replace(" ", "_").replace("-", "_").replace(".", "_").replace("ü", "ue").replace("ö", "oe").replace("ä", "ae").replace("ß", "ss")

def bpy_color_to_hex(bpy_color):
    """Konvertiert Blender-Farbwerte in das HEX-Format für Three.js."""
    rgb = tuple(int(channel * 255) for channel in bpy_color)
    return '0x{:02x}{:02x}{:02x}'.format(*rgb)

def addobjprop(object):
    """Generiert Position und Rotation für ein Objekt."""
    location = object.location
    rotation = object.rotation_euler
    # Konvertiere die Positionen und Rotationen von Blender zu Three.js
    code = f"{safe_js_name(object.name)}.position.set({location.x}, {location.z}, {-location.y});\n"
    code += f"{safe_js_name(object.name)}.rotation.set({rotation.x}, {rotation.z}, {-rotation.y});\n"
    return code

def export_obj(obj):
    """Exportiert nur sichtbare Meshes und gibt den Pfad der exportierten Datei zurück."""
    # Check if the mesh data has already been exported
    mesh_data = obj.data
    if mesh_data.name in exported_meshes:
        print(f"{obj.name} ist eine Instanz von {mesh_data.name} und wurde bereits exportiert.")
        return exported_meshes[mesh_data.name]

    # Skip export if object is hidden in render
    if obj.hide_render:
        print(f"{obj.name} wird nicht exportiert, da es im Render unsichtbar ist.")
        return None

    bpy.ops.object.select_all(action='DESELECT')
    if obj.type == "MESH" and obj.visible_get():  # Only visible Meshes
        obj.select_set(True)
        safe_name = safe_js_name(obj.name)
        export_path = path.join(export_dir, f"{safe_name}.glb")
        bpy.ops.export_scene.gltf(filepath=export_path, use_selection=True)
        obj.select_set(False)

        # Store the export path for this mesh data
        exported_meshes[mesh_data.name] = export_path
        print(f"{obj.name} wird als neues Objekt exportiert.")
        return export_path
    return None

# Initialize export directory
makedirs(export_dir, exist_ok=True)

# Needed Imports
imports = 'import * as THREE from "https://cdn.skypack.dev/three@0.129.0/build/three.module.js";\n'
imports += 'import { OrbitControls } from "https://cdn.skypack.dev/three@0.129.0/examples/jsm/controls/OrbitControls.js";\n'
imports += 'import { GLTFLoader } from "https://cdn.skypack.dev/three@0.129.0/examples/jsm/loaders/GLTFLoader.js";\n'

# Cameras
cam_code = "// CAMERAS\n"
for camera in bpy.data.cameras:
    cam_name = safe_js_name(camera.name)
    cam_code += f"// {camera.name}\n\n"
    cam_code += f"const {cam_name} = new THREE.PerspectiveCamera({camera.angle}, window.innerWidth / window.innerHeight, 0.1, 1000);\n"
    cam_code += addobjprop(bpy.data.objects[camera.name])
    cam_code += f"scene.add({cam_name});\n"
    cam_code += "\n"

# Lights
light_code = "// LIGHTS\n"
for light in bpy.data.lights:
    light_name = safe_js_name(light.name)

    if light.type == "POINT":
        light_code += f"const {light_name} = new THREE.PointLight({bpy_color_to_hex(light.color)});\n"
        location = bpy.data.objects[light.name].location
        light_code += f"{light_name}.position.set({location.x}, {location.z}, {-location.y});\n"

    elif light.type == "SPOT":
        light_object = bpy.data.objects[light.name]
        spot_size = light_object.data.spot_size
        light_code += f"const {light_name} = new THREE.SpotLight({bpy_color_to_hex(light.color)}, {light.energy}, {light.cutoff_distance}, {spot_size}, 0, 1);\n"
        light_code += f"{light_name}.castShadow = true;\n"

        location = light_object.location
        light_code += f"{light_name}.position.set({location.x}, {location.z}, {-location.y});\n"

        if light_object.constraints:
            for constraint in light_object.constraints:
                if constraint.type in {'TRACK_TO', 'DAMPED_TRACK', 'LOCKED_TRACK'} and constraint.target:
                    target_location = constraint.target.location
                    break
        else:
            target_location = location + light_object.rotation_euler.to_matrix() @ Vector((0, 0, -1))

        light_code += f"{light_name}.target.position.set({target_location.x}, {target_location.y}, {target_location.z});\n"

    elif light.type == "AREA":
        light_code += f"const {light_name} = new THREE.DirectionalLight({bpy_color_to_hex(light.color)}, {light.energy});\n"

    light_code += f"scene.add({light_name});\n\n"

# Objects
obj_code = "// OBJECTS\n"
loader_code = "const loader = new GLTFLoader();\n"

processed_objects = {}  # Save exported meshes
instance_counters = {}  # Count instances for every mesh

for obj in bpy.data.objects:
    if obj.type == "MESH" and obj.visible_get():  # Only export visible Meshes
        # Base name without suffixes (.001, .002, etc.)
        base_name = obj.name.split('.')[0]
        export_path = export_obj(obj)

        if export_path:
            safe_base_name = safe_js_name(base_name)  # Use only base name
            if safe_base_name not in processed_objects:
                # Only for the first instance
                loader_code += f"\n// {safe_base_name} (Instanz)\n"
                loader_code += f"loader.load('exported_gltfs/{safe_base_name}.glb',\n"
                loader_code += "\t(gltf) => {\n"
                loader_code += f"\t\tconst {safe_base_name} = gltf.scene;\n"
                loader_code += addobjprop(obj)
                loader_code += f"\t\tscene.add({safe_base_name});\n"
                loader_code += "\t},\n"
                loader_code += "\t(xhr) => {\n"
                loader_code += f"\t\tconsole.log('{safe_base_name} loaded: ' + (xhr.loaded / xhr.total * 100) + '%');\n"
                loader_code += "\t},\n"
                loader_code += "\t(error) => {\n"
                loader_code += f"\t\tconsole.error('An error happened loading the model {safe_base_name}', error);\n"
                loader_code += "\t}\n"
                loader_code += ");\n"
                processed_objects[safe_base_name] = export_path
                instance_counters[safe_base_name] = 1  # Zähler für Instanzen beginnen bei 1
            else:
                # Reinstantiate existing meshes
                instance_name = f"{safe_base_name}_{str(instance_counters[safe_base_name]).zfill(3)}"
                instance_counters[safe_base_name] += 1  # Zähler erhöhen
                loader_code += f"\n// Instanz von {safe_base_name} ({instance_name})\n"
                loader_code += f"const {instance_name} = {safe_base_name}.clone();\n"
                loader_code += addobjprop(obj)
                loader_code += f"scene.add({instance_name});\n"

# Renderer
renderer_code = "// RENDERER\n"
renderer_code += "const renderer = new THREE.WebGLRenderer();\n"
renderer_code += "renderer.setSize(window.innerWidth, window.innerHeight);\n"
renderer_code += "document.body.appendChild(renderer.domElement);\n"
renderer_code += f"scene.background = new THREE.Color({bpy_color_to_hex(bpy.context.scene.world.color)});\n"

# Events and Animations
renderer_code += "\n// Event Listeners\n"
renderer_code += "window.addEventListener('resize', () => {\n"
renderer_code += f"\t{bpy.data.cameras[0].name}.aspect = window.innerWidth / window.innerHeight;\n"
renderer_code += f"\t{bpy.data.cameras[0].name}.updateProjectionMatrix();\n"
renderer_code += "\trenderer.setSize(window.innerWidth, window.innerHeight);"
renderer_code += "});\n"
renderer_code += "\nfunction animate() {\n"
renderer_code += "\trequestAnimationFrame(animate);\n"
renderer_code += f"\trenderer.render(scene, {bpy.data.cameras[0].name});\n"
renderer_code += "}\n"
renderer_code += "animate();\n"

# Export in three.js
with open(path.join(blend_dir, "three.js"), "w") as file:
    file.write(imports)
    file.write("const scene = new THREE.Scene();\n")
    file.write(cam_code)
    file.write(light_code)
    file.write(obj_code)
    file.write(loader_code)
    file.write(renderer_code)

print("Export finished!")