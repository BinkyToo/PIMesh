import os
import shutil
import termcolor

from enum import Enum
from network import Link, Network


print("\x1B[22t") # Save window title

Mode = Enum('Mode', ('list', 'links', 'help'))
mode_names = {
    Mode.list: "Entity List",
    Mode.links: "Single entity view",
    Mode.help: "Documentation"
}
current_mode = Mode.list

class UI:
  def __init__(self, lines, cols):
    self.mode = Mode.list
    self.status = "Started PIMesh"
    self.lines = lines
    self.cols = cols

UI = UI(shutil.get_terminal_size()[0], shutil.get_terminal_size()[1])

print("\x1B]0;%s\x07" % "PIMesh") # Set window title

filename = "network0.pimesh"            # Currently fixed filename - should it really be an argument when starting the script?

try:
    network = Network.from_file(open(filename))
    UI.status = "Loaded PIMesh network from file"
except FileNotFoundError:
    network = Network()
    UI.status = "Created empty network (file not found)"

def print_entity_list():
    """Print a list of entitites which have one of more links to/from them"""
    #global UI.status
    if len(network) == 0:
        print("(No entities in network)")           # Could be slightly confusing, but saves a big empty space
        return 1
    for n, name in enumerate(network.origins):
        print(str(n) + " | " + name)
    return len(network)         # number of lines printed by this function, needed to pad vertically by the right amount


def print_links(name):
    """Print a list of links associated with a specific entity"""
    print(name + ':\n')
    for n, link in enumerate(network[name]):
        print(str(n) + " | " + link.tag + ": " + link.target)
    return len(network[name])+2 # number of lines printed by this function, needed to pad vertically by the right amount


def print_help():
    """Display documentation"""
    #global UI.status
    #print("Sorry, help not implemented yet")          # FIXME
    for command in commands:
      print(command.names[0])
      print("  " + command.__doc__ + '\n')
    return len(commands)*3                    # number of lines printed by this function, needed to pad vertically by the right amount


def split_input(user_input):
    """Split user input into a command and a list of arguments"""
    command, *arguments = user_input.split(" ", 1)
    if len(arguments) > 0:
        arguments = arguments[0].split(": ")
    return command, arguments

#-----------------

def command_quit(arguments):
    """Trigger a clean exit from the program, saving changes"""
    global quitting
    quitting = True
    return 'Now quitting'

command_quit.names = ['quit', 'exit']
command_quit.accepted_args = [0]
command_quit.applicable_modes = [Mode.links, Mode.list, Mode.help]

def command_list(arguments):
    """list entities which have associated links"""
    global current_mode
    current_mode = Mode.list
    #current_entity.addlink(arguments[0], arguments[1])
    return 'Now listing all entities'

command_list.names = ['list', 'ls']
command_list.accepted_args = [0]
command_list.applicable_modes = [Mode.links, Mode.help]

def command_view(arguments):
    """View the links associated with a specified entity, creating that entity if required"""
    global current_mode, current_name
    current_mode = Mode.links
    current_name = arguments[0]
    return 'Now viewing entity "' + current_name + '"'

command_view.names = ['view', 'vw']
command_view.accepted_args = [1]
command_view.applicable_modes = [Mode.links, Mode.help, Mode.list]

def command_remove(arguments):
    """Remove a specific link associated with the current entity"""
    global current_name
    tag, target, *rest = arguments[0], arguments[1]
    inverse_tag = rest[0] if rest else Network.reciprocal(tag)
    try:
        network.unlink(current_name, tag, target, inverse_tag)
        return 'Removed link "' + tag + ": " + target + '"'
    except ValueError:
        return "No such link."

command_remove.names = ['remove', 'rm']
command_remove.accepted_args = [2]
command_remove.applicable_modes = [Mode.links]

def command_add(arguments):
    """Add a new link to the current entity"""
    global current_name
    tag, target, *rest = arguments[0], arguments[1]
    inverse_tag = rest[0] if rest else Network.reciprocal(tag)
    try:
        network.addlink(current_name, tag, target, inverse_tag)
        return 'Added link "' + tag + ": " + target + '"'
    except ValueError:
        return "Link already existed."

command_add.names = ['add', 'ad']
command_add.accepted_args = [2]
command_add.applicable_modes = [Mode.links]

def command_update(arguments):
    """Change the target of one of the current entity's links"""
    global current_name
    tag = arguments[0]
    if (len(arguments) == 2):
        old_target, new_target = (...), arguments[1]
    else:
        old_target, new_target = arguments[1:]

    to_replace = network[current_name, tag, old_target]
    if not len(to_replace):
        return '"' + tag + ': ' + old_target + '" - no such link for this entity'
    if len(to_replace) > 1:
        return 'Sorry, tag "' + tag + '" is ambiguous.'
    inverse_tag = to_replace[0].inverse_tag
    to_replace.unlink()
    network.addlink(current_name, tag, new_target, inverse_tag)

    return 'Updated link from "' + tag + ': ' + old_target + '" to "' + tag + ': ' + new_target + '"'

command_update.names = ['update', 'ud']
command_update.accepted_args = [2, 3]
command_update.applicable_modes = [Mode.links]

def command_help(arguments):
    """display documentation"""
    global current_mode
    current_mode = Mode.help
    return 'Now viewing documentation'

command_help.names = ['help', 'man', '?']
command_help.accepted_args = [0]
command_help.applicable_modes = [Mode.links, Mode.list]

#-----------------

commands = (
    command_list,
    command_view,
    command_remove,
    command_add,
    command_update,
    command_help,
    command_quit
)


def process_command(invocation, arguments):
    global quitting, current_mode, current_name, UI       # Not sure if globals are nice or not...
    
    for command in commands:
        if invocation in command.names:
            if len(arguments) not in command.accepted_args:
                UI.status = command.names[0] + ": Unacceptable number of arguments"
                break
            if current_mode not in command.applicable_modes:
                UI.status = command.names[0] + ": Inappropriate mode"
                break
            UI.status = command(arguments)
            break
    else:
        try:
            if current_mode == Mode.links:
                goto = network[current_name].targets[int(invocation)]
                UI.status = command_view((goto,))
            elif current_mode == Mode.list:
                UI.status = command_view((network[int(invocation)].origin,))
            else:
                UI.status = "Numeric shortcuts don't work in this mode"
        except IndexError:
            UI.status = invocation + " - invalid index"
        except ValueError:
            UI.status = invocation + " - not a command"


quitting = False
while not quitting:
    UI.cols, UI.lines = shutil.get_terminal_size()
    os.system("clear")
    if current_mode == Mode.list:               # Elif chains are ugly - FIXME
        used_lines = print_entity_list()
    elif current_mode == Mode.links:
        used_lines = print_links(current_name)
    elif current_mode == Mode.help:
        used_lines = print_help()
    else:
        UI.status = "Error: Unknown current_mode!"

    used_lines += 3
    print("\n" * (UI.lines - used_lines))            # Pad vertically so that the command prompt is at the bottom of the terminal
    UI.status_line = " " + UI.status + (" " * (UI.cols - len(UI.status) - 1))
    termcolor.cprint(UI.status_line, attrs=['reverse'])
    command, arguments = split_input(input("> "))
    process_command(command, arguments)


os.system("clear")
try:
    network.to_file(open(filename, 'w'))
    print("Saved session changes to file. \nPIMesh quitting...")
except:
    print("Saving to file failed!")

print("\x1B[23t")		#restore window title
