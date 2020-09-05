import csv
import json
import os
import sys
import datetime

import bpy

blend_dir = os.path.dirname(bpy.data.filepath)
if blend_dir not in sys.path:
    sys.path.append(blend_dir)

import car_customize
import car_explosions
import importlib

importlib.reload(car_customize)

argv = sys.argv
try:
    local_args = argv[argv.index("--") + 1:]  # get all args after "--"
    render_dir = local_args[0]
except ValueError:
    local_args = []
    render_dir = bpy.data.scenes["Scene"].render.filepath

max_frame = 500

# setup filepath directories to allow script to run in ide or blender
rel_path = ""
blender_script_dir = os.path.dirname(__file__)
if blender_script_dir.endswith('.blend'):
    rel_path = "/.."

blend_rel_path = blender_script_dir + rel_path
data_prep_path = blend_rel_path + "/data_prep/"
race_data_path = data_prep_path + "race_data_best_3laps"
texture_path = blend_rel_path + "/Textures"

with open(race_data_path + f"/race_data.json") as f:
    fileData = json.load(f)


def getRaceCoords(plot_file_path):
    csv_filepath = data_prep_path + plot_file_path
    with open(csv_filepath) as csvfile:
        reader = csv.reader(csvfile, quoting=csv.QUOTE_NONNUMERIC)
        next(reader, None)
        return list(reader)


def getAddedCoordsForStartingPosition(team_position, first_coord):
    max_move_x = 10
    incremental = max_move_x / len(fileData)
    x_translate = (incremental * team_position) + .4
    if team_position % 2 != 0:
        y_translate = .2
    else:
        y_translate = -.15

    current_x = first_coord[0]
    current_y = first_coord[1]
    first_x = current_x - x_translate
    second_x = current_x - 0.3
    third_x = current_x - 0.1
    first_y = current_y - y_translate

    coord_list = []
    coord_list.append([first_x, first_y])
    coord_list.append([second_x, first_y])
    coord_list.append([third_x, first_y])
    return coord_list


def generatePath(coords, racer_number, total_frames):
    curve_name = "racer_" + str(racer_number) + "_curve"
    # make a new curve
    crv = bpy.data.curves.new('crv_' + str(racer_number), 'CURVE')
    crv.dimensions = '2D'

    starting_coords = getAddedCoordsForStartingPosition(racer_number, coords[0])
    updated_coords = starting_coords + coords

    # make a new spline in that curve
    spline = crv.splines.new(type='NURBS')
    # a spline point for each point - already contains 1 point
    spline.points.add(len(updated_coords) - 1)

    # assign the point coordinates to the spline points
    for p, new_co in zip(spline.points, updated_coords):
        p.co = (new_co + [0] + [1.0])

    # make a new object with the curve
    new_curve = bpy.data.objects.new(curve_name, crv)
    bpy.context.scene.collection.objects.link(new_curve)

    # update path duration
    crv.path_duration = total_frames

    # check if slowest car
    global max_frame
    if(total_frames + 50 > max_frame):
        max_frame = total_frames + 50

    return new_curve


def assignCarToPath(curve, iterString):
    objects = bpy.data.objects
    car_base = objects['car_base' + iterString]

    bpy.ops.object.select_all(action='DESELECT')

    curve.select_set(True)
    car_base.select_set(True)

    bpy.context.view_layer.objects.active = curve
    bpy.ops.object.parent_set(type="FOLLOW")
    explode_color = objects['explode-sprite-color' + iterString]
    explode_color.hide_render = True
    explode_shadow = objects['explode-sprite-shadow' + iterString]
    explode_shadow.hide_render = True


for i in range(len(fileData)):
    # add cars to scene
    car_collection_path = blend_rel_path + "/race_car.blend/Collection"
    bpy.ops.wm.append(
        directory=car_collection_path,
        link=False, filename="race_car")


def getIterString(team_position):
    iterString = ''
    if team_position > 0:
        iterString = "." + str(team_position).zfill(3)

    return iterString


for i in fileData:
    team_position = int(i['starting_position'])
    iterString = getIterString(team_position)
    team_name = i['team']
    car_number = i['car_no']
    car_color = i['car_color']
    car_time = i['lap_time']
    crashed = i['lap_end_state']
    plot_file_path = i['plot_file']
    total_frames = 24 * car_time
    print("Rendering race data for " + team_name)

    print("  Get coordinates plot")
    coords = getRaceCoords(plot_file_path)

    print("  Generating Path")
    curve = generatePath(coords, team_position, total_frames)

    print("  Generating Car")
    car_customize.modifyCarAttributes(texture_path, iterString, car_number, car_color)

    print("  Assign car to follow path")
    assignCarToPath(curve, iterString)

    if crashed == 'off_track':
        print("  !!! Add explosion to car " + team_name)
        car_explosions.addExplosion(iterString, total_frames)

# set animation duration
bpy.context.scene.frame_end = max_frame

today = datetime.date.today()
race_blend_path = f"{bpy.path.abspath('//')}race_{today}.blend"
print(f"\nSaving race blend file as: {race_blend_path}")
bpy.ops.wm.save_as_mainfile(filepath=race_blend_path)

start_grid_blend_path = f"{bpy.path.abspath('//')}starting_grid_{today}.blend"
print(f"\nCreate Starting Grid and saving file as: {start_grid_blend_path}")

for i in fileData:
    iterString = getIterString(int(i['starting_position']))
    car_base = bpy.data.objects[f'car_base{iterString}']
    bpy.ops.object.select_all(action='DESELECT')
    car_base.select_set(True)
    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')

bpy.ops.wm.save_as_mainfile(filepath=start_grid_blend_path)


# print("\nRendering animation")
# bpy.data.scenes["Scene"].render.filepath = f'{render_dir}/{current_time}/'
# bpy.ops.render.render(animation=True)