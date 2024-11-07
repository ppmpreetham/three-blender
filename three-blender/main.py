import bpy
from mathutils import Vector

def bpy_color_to_hex(bpy_color):
    rgb = tuple(int(channel * 255) for channel in bpy_color)
    return '0x{:02x}{:02x}{:02x}'.format(*rgb)

def addobjprop(object):
    location = bpy.data.objects[object.name].location
    rotation = bpy.data.objects[object.name].rotation_euler

    code = f"{object.name}.position.set({location.x}, {location.y}, {location.z});\n"
    code += f"{object.name}.rotation.set({rotation.x}, {rotation.y}, {rotation.z});\n"

    return code

# CAMERAS

cam_code = ""

for camera in bpy.data.cameras:
    cam_code += f"const {camera.name} = new THREE.PerspectiveCamera({camera.lens}, window.innerWidth / window.innerHeight, 0.1, 1000);\n"
    cam_code += addobjprop(camera)
    cam_code += "\n"

print(cam_code)

# LIGHTS

light_code = ""

for light in bpy.data.lights:

    if light.type == "POINT":
        light_code += f"const {light.name} = new THREE.PointLight({bpy_color_to_hex(light.color)});\n"

    elif light.type == "SPOT":
        light_object = bpy.data.objects[light.name]
        spot_size = light_object.data.spot_size

        light_code += f"const {light.name} = new THREE.SpotLight({bpy_color_to_hex(light.color)}, {light.energy}, {light.cutoff_distance}, {spot_size}, 0, 1);\n"
        light_code += f"{light.name}.castShadow = true; // enable shadow\n"

        location = light_object.location

        # If there's a target constraint, use that, else, calculate a default target location
        if light_object.constraints:
            for constraint in light_object.constraints:
                if constraint.type in {'TRACK_TO', 'DAMPED_TRACK', 'LOCKED_TRACK'} and constraint.target:
                    target_location = constraint.target.location
                    break

        else:
            target_location = location + light_object.rotation_euler.to_matrix() @ Vector((0, 0, -1))
        light_code += f"{light.name}.target.position.set({target_location.x}, {target_location.y}, {target_location.z});\n"

    elif light.type == "AREA":
        light_code += f"const {light.name} = new THREE.DirectionalLight({bpy_color_to_hex(light.color)}, {light.energy});\n"
        
    # light position
    location = bpy.data.objects[light.name].location
    light_code += f"{light.name}.position.set({location.x}, {location.y}, {location.z});\n"

    light_code += f"scene.add({light.name});\n\n"

print(light_code)