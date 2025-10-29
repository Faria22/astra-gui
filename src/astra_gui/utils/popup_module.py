import tkinter as tk
from tkinter import messagebox


def idle_processor_popup(idle_cpu: str, cpu_per: int) -> bool:
    return messagebox.askyesno(
        'No idle thread found!',
        f"""No idle threads were found. The most idle thread is {idle_cpu} at {cpu_per}%.
Would you like to run this calculation on this thread?""",
    )


def overwrite_warning_popup() -> bool:
    return messagebox.askyesno(
        'WARNING!',
        """This will overwrite all the astra related files in this folder!
Do you wish to continue?""",
    )


def calculation_is_running_popup(name: str) -> bool:
    return messagebox.askyesno(
        'Calculation is already running!',
        f'{name} is already running. Would you like to run this anyway?',
    )


def missing_required_calculation_popup(program: str = '') -> None:
    if not program:
        program = 'Missing calculation'
    messagebox.showerror(
        'Missing Required Calculation!',
        f'{program} is required before running this program.',
    )


def not_gui_pulse_file_popup() -> None:
    messagebox.showerror(
        'Not a pulse file from the GUI!',
        """At this moment the GUI can't read pulse files that were not made by the GUI.
For now, the only option is to recreate the file in the GUI so it can be read by it again later.""",
    )


def required_field_popup(field: str) -> None:
    messagebox.showerror(
        'Required field missing!',
        f'{field.capitalize()} is a required field and must be inputted to save the file.',
    )


def directory_popup() -> None:
    messagebox.showerror(
        'No directory selected!',
        'Please select a directory before moving forward.',
    )


def completed_calculation_popup(message: str) -> None:
    messagebox.showinfo('Completed Calculation!', message)


def missing_script_file_popup(name: str) -> None:
    messagebox.showerror('Missing script file!', f'Please save the script for {name} before running!')


def help_popup() -> None:
    messagebox.showinfo('Help', 'Help menu coming soon. For now, please refer to the github.')


def about_popup() -> None:
    messagebox.showinfo(
        'About',
        """ASTRA is written by Juan Randazzo, Carlos Marante, Siddhartha Chatoopadhyay, and Luca Argenti.
GUI written by Felipe Faria.""",
    )


class NotificationHelpPopup(tk.Toplevel):
    def __init__(self, content: str) -> None:
        super().__init__()
        self.title('How to set up notification')
        self.geometry('600x600')

        text = tk.Text(self, wrap='word', highlightthickness=0, bd=0)
        text.pack(expand=True, fill='both')

        text.insert('1.0', content)
        text.config(state='disabled')

        self.bind('<Control-q>', lambda _event: self.destroy())
        self.bind('<Command-w>', lambda _event: self.destroy())


def missing_output_popup(program: str) -> None:
    messagebox.showerror(
        'Missing output!',
        f'No output from {program} found! Please run {program} before trying to get outputs.',
    )


def missing_required_file_popup(file: str) -> None:
    messagebox.showerror(
        'Required file missing!',
        f'{file} was not found in the current directory! It is a required file for this calculation.',
    )


def invalid_input_popup(message: str) -> None:
    messagebox.showerror('Invalid Input!', message)


def warning_popup(message: str) -> None:
    messagebox.showwarning('Warning!', f'Warning: {message}')


def missing_symmetry_popup(sym: str, source: str = '', root: str = '') -> None:
    if root == 'cc':
        text = 'defined in the CC basis'
    elif root == 'computed':
        text = 'a previously computed symmetry'
    elif root == 'strut':
        text = 'a calculated symmetry'
    else:
        text = 'a symmetry previously added'

    # Source just means where the ket sym is coming from, e.g., Ket symmetries for the dipoles.
    if source:
        source = f' for the {source}'

    messagebox.showerror(
        'Missing symmetry!',
        f'{sym} ket symmetry{source} is not {text}.',
    )


def create_path_popup(path: str) -> bool:
    return messagebox.askyesno(
        'Path does not exist!',
        f'The path "{path}" does not exist.\n\nWould you like to create it?',
    )
