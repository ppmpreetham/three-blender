import bpy
from mathutils import Vector
from os import makedirs, path

blend_dir = bpy.path.abspath("//")
export_dir = path.join(blend_dir, "exported_gltfs")

imports = 'import * as THREE from "https://cdn.skypack.dev/three@0.129.0/build/three.module.js";\n'
imports += 'import { OrbitControls } from "https://cdn.skypack.dev/three@0.129.0/examples/jsm/controls/OrbitControls.js";\n'
imports += 'import { GLTFLoader } from "https://cdn.skypack.dev/three@0.129.0/examples/jsm/loaders/GLTFLoader.js";\n'

# Safe importing files
def safe_name(name: str):
    return name.replace(" ", "_").replace("-", "_").replace(".", "_").replace("ü", "ue").replace("ö", "oe").replace("ä", "ae").replace("ß", "ss")

# Safe Tramsforms
def safe_transform(transform):
    return f"{transform.x}, {transform.z}, {-transform.y}"

# Convert Blender color to HEX (Three.js format)
def bpy_color_to_hex(bpy_color):
    rgb = tuple(int(channel * 255) for channel in bpy_color)
    return '0x{:02x}{:02x}{:02x}'.format(*rgb)

# Generate position and rotation properties for objects
def addobjprop(object):
    location = object.location
    rotation = object.rotation_euler
    code = f"{safe_name(object.name)}.position.set({safe_transform(location)});\n"
    code += f"{safe_name(object.name)}.rotation.set({safe_transform(rotation)});\n"
    return code

# CAMERAS
cam_code = "// CAMERAS\n"
for camera in bpy.data.cameras:
    cam_code += f"// {safe_name(camera.name)}\n\n"
    cam_code += f"const {safe_name(camera.name)} = new THREE.PerspectiveCamera({bpy.data.cameras[0].lens}, window.innerWidth / window.innerHeight, 0.1, 1000);\n"
    cam_code += addobjprop(bpy.data.objects[safe_name(camera.name)])
    cam_code += f"console.log('Camera {safe_name(camera.name)} position:', {safe_name(camera.name)}.position);\n"
    cam_code += f"scene.add({safe_name(camera.name)});\n"
    cam_code += "\n"

# LIGHTS
light_code = "// LIGHTS\n"
for light in bpy.data.lights:
    try:
        # POINT LIGHT
        if light.type == "POINT":
            light_code += f"const {safe_name(light.name)} = new THREE.PointLight({bpy_color_to_hex(light.color)});\n"
            location = bpy.data.objects[safe_name(light.name)].location
            light_code += f"{safe_name(light.name)}.position.set({safe_transform(location)});\n"

        # SPOT LIGHT
        elif light.type == "SPOT":
            light_object = bpy.data.objects[safe_name(light.name)]
            spot_size = light_object.data.spot_size
            light_code += f"const {safe_name(light.name)} = new THREE.SpotLight({bpy_color_to_hex(light.color)}, {light.energy}, {light.cutoff_distance}, {spot_size}, 0, 1);\n"
            light_code += f"{safe_name(light.name)}.castShadow = true; // enable shadow\n"
            
            location = light_object.location
            # light_code += f"{safe_name(light.name)}.position.set({location.x}, {location.y}, {location.z});\n"
            
            # Determining target location based on constraints
            if light_object.constraints:
                for constraint in light_object.constraints:
                    if constraint.type in {'TRACK_TO', 'DAMPED_TRACK', 'LOCKED_TRACK'} and constraint.target:
                        target_location = constraint.target.location
                        break
            else:
                # Calculate the target position if no constraint
                target_location = location + light_object.rotation_euler.to_matrix() @ Vector((0, 0, -1))
            
            light_code += f"{safe_name(light.name)}.target.position.set({safe_transform(target_location)});\n"

        # AREA LIGHT
        elif light.type == "AREA":
            light_code += f"const {safe_name(light.name)} = new THREE.DirectionalLight({bpy_color_to_hex(light.color)}, {light.energy});\n"
        
        light_code += f"scene.add({safe_name(light.name)});\n\n"
    except KeyError:
        print(f"Warning: Light object '{light.name}' not found in bpy.data.objects")
        continue

# OBJECTS
obj_code = "// OBJECTS\n"

def fix_filepath(filepath):
    return filepath.replace("\\", "/")

def loader(filepath, object):
    location = bpy.data.objects[safe_name(object.name)].location
    rotation = bpy.data.objects[safe_name(object.name)].rotation_euler

    load_code = f"loader.load('exported_gltfs/{safe_name(object.name)}.glb',\n"
    load_code += "\t(gltf) => {\n"
    load_code += f"\t\tconst {safe_name(object.name)} = gltf.scene;\n"
    load_code += f"\t\t{safe_name(object.name)}.position.set({safe_transform(location)});\n"
    load_code += f"\t\t{safe_name(object.name)}.rotation.set({safe_transform(rotation)});\n"
    load_code += f"\t\tscene.add({safe_name(object.name)});\n"
    load_code += "\t},\n"
    load_code += "\t(xhr) => {\n"
    load_code += f"\t\tconsole.log('{safe_name(object.name)} loaded: ' + (xhr.loaded / xhr.total * 100) + '%');\n"
    load_code += "\t},\n"
    load_code += "\t(error) => {\n"
    load_code += f"\t\tconsole.error('An error happened loading the model {safe_name(object.name)}', error);\n"
    load_code += "\t}\n"
    load_code += ");\n"
    return load_code

def export_obj(obj):
    bpy.ops.object.select_all(action='DESELECT')

    if obj.type == "MESH":
        obj.select_set(True)
        export_path = path.join(export_dir, f"{safe_name(obj.name)}.gltf")
        bpy.ops.export_scene.gltf(filepath=export_path, use_selection=True)
        obj.select_set(False)
        return export_path

# Check if GLTFLoader is needed
if bpy.data.objects:
    obj_code += "const loader = new GLTFLoader();\n"
    makedirs(export_dir, exist_ok=True)  # Create directory if it doesn't exist

for obj in bpy.data.objects:
    if obj.type == "MESH":
        obj_code += f"\n// {safe_name(obj.name)}\n"
        filepath = export_obj(obj)
        if filepath:
            obj_code += loader(filepath, obj) + "\n"

# RENDERER
renderer_code = "// RENDERER\n"
renderer_code += "const renderer = new THREE.WebGLRenderer();\n"
renderer_code += "renderer.setSize(window.innerWidth, window.innerHeight);\n"
renderer_code += "document.body.appendChild(renderer.domElement);\n"

# Background color
background_color = bpy.context.scene.world.color
renderer_code += f"\n// Background Color\n"
renderer_code += f"scene.background = new THREE.Color({bpy_color_to_hex(background_color)});\n"

# event listeners
renderer_code += "\n// Event Listeners\n"
renderer_code += "window.addEventListener('resize', () => {\n"
renderer_code += f"\t{safe_name(bpy.data.cameras[0].name)}.aspect = window.innerWidth / window.innerHeight;\n"
renderer_code += f"\t{safe_name(bpy.data.cameras[0].name)}.updateProjectionMatrix();\n"
renderer_code += "\trenderer.setSize(window.innerWidth, window.innerHeight);"
renderer_code += "});\n"

#Orbit Controls
renderer_code += "\n// OrbitControls\n";
renderer_code += "const controls = new OrbitControls(" + safe_name(bpy.data.cameras[0].name) + ", renderer.domElement);\n";
renderer_code += "controls.enableDamping = true;\n";
renderer_code += "controls.dampingFactor = 0.05;\n";

# Animation loop
renderer_code += "\nfunction animate() {\n"
renderer_code += "\trequestAnimationFrame(animate);\n"
renderer_code += f"\trenderer.render(scene, {safe_name(bpy.data.cameras[0].name)});\n"
renderer_code += "}\n"
renderer_code += "animate();\n"

print(imports)
print("const scene = new THREE.Scene();")
print(cam_code)
print(light_code)
print(obj_code)
print(renderer_code)

# Save the code to a file
with open(path.join(blend_dir, "three.js"), "w") as file:
    file.write(imports)
    file.write("const scene = new THREE.Scene();\n")
    file.write(cam_code)
    file.write(light_code)
    file.write(obj_code)
    file.write(renderer_code)
    file.close()