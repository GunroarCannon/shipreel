extends SceneTree
## shipreel autoplay driver — used by `clip.py record-godot --autoplay timeline.json`.
## Runs a scene under Movie Maker and replays scripted input. Nothing in the project is edited:
## this file is passed with --script, it loads the project's autoloads itself, then the scene.
##
## timeline.json:
## {"scene": "res://main.tscn",             (optional; else --scene, else the project's main scene)
##  "events": [
##    {"t": 0.5, "action": "ui_accept"},                  tap an input action
##    {"t": 1.0, "action": "move_right", "hold": 1.5},    hold an action for 1.5 s
##    {"t": 3.0, "key": "SPACE"},                          tap a key (Key enum name without KEY_)
##    {"t": 3.5, "key": "W", "hold": 0.8},
##    {"t": 4.0, "click": [640, 360]},                     left click at viewport coords
##    {"t": 4.5, "mouse": [700, 300]},                     move mouse
##    {"t": 5.0, "call": ["/root/Main", "spawn_boss"]},    call a method (demo shortcuts, debug cheats)
##    {"t": 6.0, "set": ["/root/Main/Player", "speed", 900]}
##  ]}
## Env toggles (e.g. DEBUG_OVERLAY=0) are passed with clip.py --env KEY=VALUE.

var events: Array = []
var clock := 0.0
var held_actions := {}
var held_keys := {}


func _initialize() -> void:
	var data = {}
	var path := OS.get_environment("SHIPREEL_AUTOPLAY")
	if path != "" and FileAccess.file_exists(path):
		data = JSON.parse_string(FileAccess.get_file_as_string(path))
	var scene := OS.get_environment("SHIPREEL_SCENE")
	if scene == "" and data is Dictionary and data.has("scene"):
		scene = data["scene"]
	if scene == "":
		scene = ProjectSettings.get_setting("application/run/main_scene", "")
	events = data.get("events", []) if data is Dictionary else []
	events.sort_custom(func(a, b): return float(a["t"]) < float(b["t"]))
	_apply_resolution()
	_load_autoloads()
	if scene != "":
		change_scene_to_file(scene)


func _apply_resolution() -> void:
	# Projects often pin window_width/height_override, which makes --resolution a no-op under Movie Maker.
	# SHIPREEL_RES=WxH (set by clip.py --resolution) resizes the root window itself, so a portrait capture really is portrait.
	var r := OS.get_environment("SHIPREEL_RES").split("x")
	if r.size() != 2:
		return
	var size := Vector2i(int(r[0]), int(r[1]))
	if size.x < 16 or size.y < 16:
		return
	root.size = size
	DisplayServer.window_set_size(size)


func _load_autoloads() -> void:
	# --script skips the project's autoloads; add them the way the engine would (in declared order)
	for prop in ProjectSettings.get_property_list():
		var key: String = prop["name"]
		if not key.begins_with("autoload/"):
			continue
		var autoload_name := key.substr(9)
		if root.has_node(autoload_name):
			continue
		var p: String = str(ProjectSettings.get_setting(key)).trim_prefix("*")
		var res = load(p)
		var node: Node = null
		if res is PackedScene:
			node = res.instantiate()
		elif res is Script:
			node = res.new()
		if node:
			node.name = autoload_name
			root.add_child(node)


func _process(delta: float) -> bool:
	if current_scene == null:
		return false  # scene still loading: start the timeline at its first frame so early events aren't lost
	clock += delta
	while events.size() > 0 and float(events[0]["t"]) <= clock:
		_fire(events.pop_front())
	for a in held_actions.keys():
		if clock >= held_actions[a]:
			Input.action_release(a)
			held_actions.erase(a)
	for k in held_keys.keys():
		if clock >= held_keys[k]:
			_key(k, false)
			held_keys.erase(k)
	return false


func _fire(e: Dictionary) -> void:
	if e.has("action"):
		Input.action_press(e["action"])
		held_actions[e["action"]] = clock + float(e.get("hold", 0.1))
	elif e.has("key"):
		_key(e["key"], true)
		held_keys[e["key"]] = clock + float(e.get("hold", 0.1))
	elif e.has("click"):
		var pos := Vector2(e["click"][0], e["click"][1])
		_mouse_move(pos)
		for pressed in [true, false]:
			var ev := InputEventMouseButton.new()
			ev.button_index = MOUSE_BUTTON_LEFT
			ev.pressed = pressed
			ev.position = pos
			ev.global_position = pos
			Input.parse_input_event(ev)
	elif e.has("mouse"):
		_mouse_move(Vector2(e["mouse"][0], e["mouse"][1]))
	elif e.has("call"):
		var n := root.get_node_or_null(NodePath(e["call"][0]))
		if n and n.has_method(e["call"][1]):
			n.callv(e["call"][1], e["call"].slice(2))
	elif e.has("set"):
		var n := root.get_node_or_null(NodePath(e["set"][0]))
		if n:
			n.set(e["set"][1], e["set"][2])


func _key(name: String, pressed: bool) -> void:
	var ev := InputEventKey.new()
	ev.keycode = OS.find_keycode_from_string(name)
	ev.physical_keycode = ev.keycode
	ev.pressed = pressed
	Input.parse_input_event(ev)


func _mouse_move(pos: Vector2) -> void:
	var ev := InputEventMouseMotion.new()
	ev.position = pos
	ev.global_position = pos
	Input.parse_input_event(ev)
