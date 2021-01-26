#!/usr/bin/python3

import sys
import gi

gi.require_version('Gtk', '3.0')
try:
    gi.require_version('GtkLayerShell', '0.1')
except ValueError:

    raise RuntimeError('\n\n' +
                       'If you haven\'t installed GTK Layer Shell, you need to point Python to the\n' +
                       'library by setting GI_TYPELIB_PATH and LD_LIBRARY_PATH to <build-dir>/src/.\n' +
                       'For example you might need to run:\n\n' +
                       'GI_TYPELIB_PATH=build/src LD_LIBRARY_PATH=build/src python3 ' + ' '.join(sys.argv))

from gi.repository import Gtk, GtkLayerShell, GLib, Gdk

from tools import *
from modules.sway_taskbar import SwayTaskbar
from modules.sway_workspaces import SwayWorkspaces
from modules.custom_button import CustomButton
from modules.executor import Executor
from modules.clock import Clock
from modules.controls import Controls
from modules.playerctl import Playerctl

try:
    from pyalsa import alsamixer
    common.pyalsa = True
except:
    print("pylsa module not found, will try amixer")


def check_tree():
    # Do if tree changed
    tree = common.i3.get_tree()
    if tree.ipc_data != common.ipc_data:
        for item in common.taskbars_list:
            item.refresh()
        for item in common.controls_list:
            if item.popup_window.get_visible():
                item.popup_window.hide()

    common.ipc_data = common.i3.get_tree().ipc_data

    return True


def instantiate_content(panel, container, content_list):
    check_key(panel, "items-padding", 0)
    check_key(panel, "icons", "light")

    for item in content_list:
        if item == "sway-taskbar":
            if "sway-taskbar" in panel:
                check_key(panel["sway-taskbar"], "all-outputs", False)
                if panel["sway-taskbar"]["all-outputs"]:
                    taskbar = SwayTaskbar(panel["sway-taskbar"])
                else:
                    taskbar = SwayTaskbar(panel["sway-taskbar"], display_name="{}".format(panel["output"]))
                common.taskbars_list.append(taskbar)
    
                container.pack_start(taskbar, False, False, panel["items-padding"])
            else:
                print("'sway-taskbar' not defined in this panel instance")
            
        if item == "sway-workspaces":
            if "sway-workspaces" in panel:
                workspaces = SwayWorkspaces(panel["sway-workspaces"])
                container.pack_start(workspaces, False, False, panel["items-padding"])
            else:
                print("'sway-workspaces' not defined in this panel instance")
                
        if "button-" in item:
            if item in panel:
                button = CustomButton(panel[item])
                container.pack_start(button, False, False, panel["items-padding"])
            else:
                print("'{}' not defined in this panel instance".format(item))
                
        if "executor-" in item:
            if item in panel:
                executor = Executor(panel[item])
                container.pack_start(executor, False, False, panel["items-padding"])
            else:
                print("'{}' not defined in this panel instance".format(item))
                
        if item == "clock":
            if item in panel:
                clock = Clock(panel[item])
                container.pack_start(clock, False, False, panel["items-padding"])
            else:
                clock = Clock({})
                container.pack_start(clock, False, False, panel["items-padding"])
                
        if item == "playerctl":
            if item in panel:
                playerctl = Playerctl(panel[item])
                container.pack_start(playerctl, False, False, panel["items-padding"])
            else:
                print("'{}' not defined in this panel instance".format(item))


def main():
    save_string(str(os.getpid()), os.path.join(temp_dir(), "nwg-panel.pid"))
    
    common.app_dirs = get_app_dirs()

    common.upower = is_command("upower")
    common.acpi = is_command("acpi")

    common.config_dir = get_config_dir()
    config_file = os.path.join(common.config_dir, "config")

    common.outputs = list_outputs()

    panels = load_json(config_file)

    screen = Gdk.Screen.get_default()
    provider = Gtk.CssProvider()
    style_context = Gtk.StyleContext()
    style_context.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    try:
        provider.load_from_path(os.path.join(common.config_dir, "style.css"))
    except Exception as e:
        print(e)

    output_to_focus = None

    for panel in panels:
        check_key(panel, "spacing", 6)
        check_key(panel, "homogeneous", False)
        check_key(panel, "css-name", "")
        common.i3.command("focus output {}".format(panel["output"]))
        window = Gtk.Window()
        if panel["css-name"]:
            window.set_property("name", panel["css-name"])
        check_key(panel, "width", common.outputs[panel["output"]]["width"])
        w = panel["width"]
        check_key(panel, "height", 0)
        h = panel["height"]

        check_key(panel, "controls", False)
        check_key(panel, "controls-settings", {})

        controls_settings = panel["controls-settings"]
        check_key(controls_settings, "alignment", "right")
        check_key(controls_settings, "show-values", False)

        Gtk.Widget.set_size_request(window, w, h)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        vbox.pack_start(hbox, True, True, panel["padding-vertical"])

        inner_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        if panel["homogeneous"]:
            inner_box.set_homogeneous(True)
        hbox.pack_start(inner_box, True, True, panel["padding-horizontal"])

        left_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=panel["spacing"])
        inner_box.pack_start(left_box, False, True, 0)
        if panel["controls"] and panel["controls-settings"]["alignment"] == "left":
            cc = Controls(panel["controls-settings"], panel["position"], panel["controls-settings"]["alignment"], int(w/6))
            common.controls_list.append(cc)
            left_box.pack_start(cc, False, False, 0)
        instantiate_content(panel, left_box, panel["modules-left"])

        center_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=panel["spacing"])
        inner_box.pack_start(center_box, True, False, 0)
        instantiate_content(panel, center_box, panel["modules-center"])

        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=panel["spacing"])
        # Damn on the guy who invented `pack_start(child, expand, fill, padding)`!
        helper_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        helper_box.pack_end(right_box, False, False, 0)
        inner_box.pack_start(helper_box, False, True, 0)
        instantiate_content(panel, right_box, panel["modules-right"])

        if panel["controls"] and panel["controls-settings"]["alignment"] == "right":
            cc = Controls(panel["controls-settings"], panel["position"], panel["controls-settings"]["alignment"], int(w/6))
            common.controls_list.append(cc)
            right_box.pack_end(cc, False, False, 0)

        window.add(vbox)

        GtkLayerShell.init_for_window(window)

        GtkLayerShell.auto_exclusive_zone_enable(window)

        check_key(panel, "layer", "top")
        if panel["layer"] == "top":
            GtkLayerShell.set_layer(window, GtkLayerShell.Layer.TOP)
        else:
            GtkLayerShell.set_layer(window, GtkLayerShell.Layer.BOTTOM)

        check_key(panel, "margin-top", 0)
        GtkLayerShell.set_margin(window, GtkLayerShell.Edge.TOP, 0)

        check_key(panel, "margin-bottom", 0)
        GtkLayerShell.set_margin(window, GtkLayerShell.Edge.BOTTOM, 0)

        check_key(panel, "position", "top")
        if panel["position"] == "top":
            GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.TOP, 1)
        else:
            GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.BOTTOM, 1)

        window.show_all()
        window.connect('destroy', Gtk.main_quit)

        """
        As we displace panels by focusing outputs, we always end up in the last output focused on start.
        Let's add the optional "focus" key to the panel placed on the primary output. Whatever non-empty value allowed.
        """
        try:
            if panel["focus"]:
                common.i3.command("focus output {}".format(panel["output"]))
                output_to_focus = panel["output"]
        except KeyError:
            pass

    if output_to_focus:
        common.i3.command("focus output {}".format(output_to_focus))
        
    if common.key_missing:
        print("Saving amended config")
        save_json(panels, os.path.join(common.config_dir, "config_amended"))

    #GLib.timeout_add(100, listener_reply)
    Gdk.threads_add_timeout(GLib.PRIORITY_DEFAULT_IDLE, 150, check_tree)
    Gtk.main()


if __name__ == "__main__":
    sys.exit(main())
