import bpy

def bpy_color_to_hex(bpy_color):
    rgb = tuple(int(channel * 255) for channel in bpy_color)
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

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
        spot_size = bpy.data.objects[light.name].data.spot_size

        light_code += f"const {light.name} = new THREE.SpotLight({bpy_color_to_hex(light.color)}, {light.energy}, {light.cutoff_distance}, {spot_size}, 0, 1);\n"
    
    light_code += addobjprop(light)
    light_code += f"scene.add({light.name});\n\n"

print(light_code)