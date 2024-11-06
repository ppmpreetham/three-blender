import bpy

def bpy_color_to_hex(bpy_color):
    rgb = tuple(int(channel * 255) for channel in bpy_color)
    return '#{:02x}{:02x}{:02x}'.format(*rgb)

def addobjprop(object):
    location = bpy.data.objects[object.name].location
    rotation = bpy.data.objects[object.name].rotation_euler

    code = f"{object.name}.position.set({location.x}, {location.y}, {location.z});\n"
    code += f"{object.name}.position.set({rotation.x}, {rotation.y}, {rotation.z});\n"

    return code

# CAMERAS

cam_code = ""

for camera in bpy.data.cameras:
    print("\n")    
    cam_code += f"const {camera.name} = new THREE.PerspectiveCamera({camera.lens}, window.innerWidth / window.innerHeight, 0.1, 1000);\n"
    cam_code +=addobjprop(camera)

print(cam_code)

# LIGHTS

light_code = ""

for i in bpy.data.lights:


    light_loc = bpy.data.objects[i.name].location
    light_rot = bpy.data.objects[i.name].rotation_euler

    print("LIGHT NAME: ", i.name)
    # print("LIGHT LOCATION: ", light_loc)
    # print("LIGHT ROTATION: ", light_rot)
    print("LIGHT TYPE: ", i.type)
    # print("LIGHT COLOR: ", i.color)


    if i.type == "POINT":
        print("\n")
        light_code += f"const {i.name} = new THREE.{i.type}Light({bpy_color_to_hex(i.color)});\n"
        light_code += f"{i.name}.position.set({light_loc.x}, {light_loc.y}, {light_loc.z});\n"

    elif i.type == "SPOT":
        print("\n")
        spot_size = bpy.data.objects[i.name].data.spot_size

        light_code += f"const {i.name} = new THREE.{i.type}Light({bpy_color_to_hex(i.color)}, {i.energy}, {i.cutoff_distance}, {spot_size}, );\n"
        light_code += f"{i.name}.position.set({light_loc.x}, {light_loc.y}, {light_loc.z});\n"
        light_code += f"{i.name}.rotation.set({light_rot.x}, {light_rot.y}, {light_rot.z});\n"

print(light_code)