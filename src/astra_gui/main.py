"""Entry point for the ASTRA GUI application."""

import argparse
import logging
import os
import shutil
import tkinter as tk
from pathlib import Path
from platform import system
from tkinter import filedialog, ttk
from typing import TYPE_CHECKING

from astra_gui.close_coupling.create_cc_notebook import CreateCcNotebook
from astra_gui.home_screen import HomeNotebook
from astra_gui.time_dependent.time_dependent_notebook import TimeDependentNotebook
from astra_gui.time_independent.time_independent_notebook import TimeIndependentNotebook
from astra_gui.utils.config_module import get_ssh_host, set_ssh_host
from astra_gui.utils.logger_module import log_operation, setup_logger
from astra_gui.utils.notification_module import Notification
from astra_gui.utils.popup_module import (
    NotificationHelpPopup,
    about_popup,
    create_path_popup,
    directory_popup,
    help_popup,
    overwrite_warning_popup,
)
from astra_gui.utils.ssh_client import SshClient
from astra_gui.utils.statusbar_module import StatusBar

if TYPE_CHECKING:
    from astra_gui.utils.notebook_module import Notebook

logger = logging.getLogger(__name__)


class Astra(tk.Tk):
    """Main ASTRA GUI application class."""

    def __init__(self, args: argparse.Namespace) -> None:
        super().__init__()

        self.title('ASTRA')

        self.cur_os = system()
        self.root_geometry: tuple[int, int]
        self.set_gui_geometry()

        self.minsize(self.root_geometry[0], self.root_geometry[1])

        self.astra_gui_path = Path(__file__).resolve().parent

        self.notification = Notification()

        self.ssh_client = None
        self.home_path = Path.home()
        self.running_directory = None
        if args.ssh:
            self.ssh_client = SshClient(self)
            if not (home_path := self.ssh_client.home_path):
                raise RuntimeError('Could not find home path of the ssh client')

            self.home_path = home_path

        self.bind('<Control-q>', lambda _event: self.destroy())
        self.bind('<Command-w>', lambda _event: self.destroy())

        # Status messages
        self.statusbar = StatusBar(self, 'Ready')
        self.statusbar.pack(fill=tk.X, side='bottom', ipady=5)

        # Menu bar
        self.menu()

        container = ttk.Frame(self)
        container.pack(side='top', fill='both', expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.notebooks: list[Notebook] = []
        self.get_notebooks(container)

        self.get_running_dir(args.path)

        self.show_notebook_page(args)

    def get_running_dir(
        self,
        input_path: str | None,
        new_path: bool = False,
        initial_dir: Path | None = None,
        title: str | None = None,
    ) -> None:
        """
        Get the running directory for the GUI.

        If `new_path` is giving, prompts the user to select a new path, and `cd` to it.
        If not, just moves the GUI to {input_path} if a truey `input_path` value was given.
        """
        if new_path:
            initial_dir = initial_dir or Path(self.running_directory or '').parent
            if self.ssh_client:
                input_path = self.ssh_client.browse_remote(initial_dir, title=title)
            else:
                input_path = filedialog.askdirectory(initialdir=str(initial_dir), title=title)

        if input_path is not None:  # Checks if a path was selected in the previous step
            directory_path = Path(input_path)

            # Check if path exists
            path_exists = self.ssh_client.path_exists(directory_path) if self.ssh_client else directory_path.exists()

            # If path doesn't exist, prompt user to create it
            if not path_exists:
                create_path = create_path_popup(str(directory_path))
                if create_path:
                    # Create the path
                    try:
                        if self.ssh_client:
                            stdout, stderr, exit_code = self.ssh_client.run_remote_command(
                                f'mkdir -p {directory_path}',
                            )
                            if exit_code != 0:
                                logger.error(
                                    'Failed to create remote directory %s: %s',
                                    directory_path,
                                    stderr or stdout,
                                )
                                return
                            logger.info('Created remote directory: %s', directory_path)
                        else:
                            directory_path.mkdir(parents=True, exist_ok=True)
                            logger.info('Created local directory: %s', directory_path)
                    except OSError as exc:
                        logger.error('Failed to create directory %s: %s', directory_path, exc)
                        return
                else:
                    # User chose not to create the path, so don't set it
                    logger.info('User chose not to create path: %s', directory_path)
                    return

            if not self.ssh_client:
                directory_path = directory_path.resolve()
                os.chdir(directory_path)

            try:
                relative_path = Path('~') / directory_path.relative_to(self.home_path)
            except ValueError:
                relative_path = directory_path

            self.statusbar.show_message(f'Currect directory: {relative_path}', overwrite_default_text=True)
            self.running_directory = directory_path
            logger.info('Changed running directory to %s', relative_path)
            self.reload()

    @log_operation('getting notebooks')
    def get_notebooks(self, container: ttk.Frame) -> None:
        """Initialize all notebooks."""
        notebook_classes = (
            HomeNotebook,
            CreateCcNotebook,
            TimeIndependentNotebook,
            TimeDependentNotebook,
        )
        for notebook_class in notebook_classes:
            self.notebooks.append(notebook_class(parent=container, controller=self))

    def show_notebook_page(self, args: argparse.Namespace) -> None:
        """Show the notebook page based on the runtime arguments."""
        cc_pages = [args.molecule, args.dalton, args.lucia, args.closecoupling, args.bsplines]

        ti_pages = [args.structural, args.scattering, args.pad]
        td_pages = [args.pulse]

        all_pages = cc_pages + ti_pages + td_pages

        num_selected = all_pages.count(True)
        if num_selected == 1:
            if not args.path:
                logger.error('Must give a path to select a page!')
        elif num_selected > 1:
            logger.error('More than one page option was given!')

        for notebook_ind, notebook_pages in enumerate([cc_pages, ti_pages, td_pages], 1):
            if any(notebook_pages):
                self.show_notebook(notebook_ind)
                self.notebooks[notebook_ind].select(notebook_pages.index(True))
                return

        self.show_notebook(0)  # Shows home page

    def show_notebook(self, notebook_ind: int) -> None:
        """Show the notebook for the given notebook index."""
        if self.running_directory or notebook_ind == 0:
            notebook = self.notebooks[notebook_ind]
            if notebook.showing:
                logger.info('Already showing notebook %d.', notebook_ind)
                return

            self.hide_notebooks()
            notebook.notebook_frame.grid(row=0, column=0, sticky='nsew')
            notebook.showing = True
            logger.info('Showing notebook %d.', notebook_ind)
        else:
            directory_popup()
            logger.info('No running directory previously selected.')

    @log_operation('hiding notebooks')
    def hide_notebooks(self) -> None:
        """Hide all notebooks."""
        for notebook in self.notebooks:
            if notebook.showing:
                notebook.notebook_frame.grid_forget()
                notebook.showing = False

    def set_gui_geometry(self) -> None:
        """Set the GUI geometry based on the current OS."""
        if self.cur_os == 'Linux':
            self.root_geometry = (800, 750)
        elif self.cur_os == 'Windows':
            self.root_geometry = (750, 750)
        elif self.cur_os == 'Darwin':
            self.root_geometry = (1425, 800)

        if self.cur_os != 'Linux':
            self.center_window()

    def center_window(self) -> None:
        """Centers the window by loading the user's screen size."""
        # Get screen width and height
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width, height = self.root_geometry

        # Calculate position coordinates
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        # Set the window position and size
        self.geometry(f'{width}x{height}+{x}+{y}')

    def ssh_settings_tab(self) -> None:
        """SSH settings tab."""

        def save_host_name() -> None:
            set_ssh_host(host_name_entry.get().strip())

        def connect_ssh() -> None:
            settings_window.destroy()
            if not self.ssh_client:
                self.ssh_client = SshClient(self)

        settings_window = tk.Toplevel(self)
        settings_window.title('Notification settings')

        ttk.Label(settings_window, text='Host name: ').grid(row=0, column=0)
        host_name_entry = ttk.Entry(settings_window)
        host_name_entry.grid(row=0, column=1)

        host_name_entry.insert(0, get_ssh_host())

        ttk.Button(settings_window, text='Save', command=save_host_name).grid(
            row=1,
            column=0,
            pady=5,
        )

        ttk.Button(settings_window, text='Connect', command=connect_ssh).grid(
            row=1,
            column=1,
            pady=5,
        )

    def notification_settings_tab(self) -> None:
        """Notification settings tab."""

        @log_operation('update notification label')
        def update_label(method: str) -> None:
            if not method:
                method = 'ntfy'  # If empty method is passed, set it to ntfy

            logger.debug('Button states: %s %s', ntfy_button.state(), email_button.state())

            self.notification.method = method
            if method == 'ntfy':
                label_text = 'NTFY Topic:'
                ntfy_button.state(['selected'])
                email_button.state(['!alternate', '!selected'])
            else:
                label_text = 'Email Address:'
                ntfy_button.state(['!alternate', '!selected'])
                email_button.state(['selected'])

            label.config(text=label_text)
            logger.debug('Button states: %s %s', ntfy_button.state(), email_button.state())

        settings_window = tk.Toplevel(self)
        settings_window.title('Notification settings')

        label = ttk.Label(settings_window)

        # Radio buttons to select method
        ntfy_button = ttk.Radiobutton(settings_window, text='NTFY', command=lambda: update_label('ntfy'))
        email_button = ttk.Radiobutton(settings_window, text='Email', command=lambda: update_label('email'))

        update_label(self.notification.method)

        label.grid(row=1, column=0, padx=5, pady=5)
        ntfy_button.grid(row=0, column=0, padx=5, pady=5)
        email_button.grid(row=0, column=1, padx=5, pady=5)

        # Entry field
        entry = ttk.Entry(settings_window)
        entry.grid(row=1, column=1, padx=5, pady=5)
        entry.insert(0, self.notification.string)

        ttk.Button(settings_window, text='Save', command=lambda: self.notification.save(entry.get().strip())).grid(
            row=2,
            column=0,
            columnspan=2,
            pady=10,
        )

    def menu(self) -> None:
        """Create the menu bar."""
        menu_bar = tk.Menu(self)
        self.config(menu=menu_bar)

        settings_menu = tk.Menu(menu_bar, tearoff=False)
        session_menu = tk.Menu(menu_bar, tearoff=False)
        help_menu = tk.Menu(menu_bar, tearoff=False)

        menu_bar.add_cascade(label='Settings', menu=settings_menu)
        settings_menu.add_command(label='Notifications', command=self.notification_settings_tab)
        settings_menu.add_command(label='SSH', command=self.ssh_settings_tab)

        menu_bar.add_cascade(label='Session', menu=session_menu)
        session_menu.add_command(label='Select running directory', command=lambda: self.get_running_dir('', True))
        session_menu.add_command(label='Copy files from template', command=self.copy_template)
        session_menu.add_command(label='Reload', command=self.reload)

        menu_bar.add_cascade(label='Help', menu=help_menu)
        help_menu.add_command(label='Help', command=help_popup)
        help_menu.add_command(label='About', command=about_popup)

        with (self.astra_gui_path / 'help_messages' / 'notification.md').open('r') as f:
            content = f.read()
        help_menu.add_command(label='Notification methods', command=lambda: NotificationHelpPopup(content))

    def get_process_from_notebooks(self, action: str, *args, **kwargs) -> None:
        """Get action from all the notebooks."""
        for _notebook in self.notebooks:
            getattr(_notebook, action)(*args, **kwargs)

    @log_operation('erasing in all notebooks')
    def erase(self) -> None:
        """Erase all the entries/fields in all notebooks."""
        self.get_process_from_notebooks('erase')

    @log_operation('getting inputs from all notebooks')
    def get_inputs(self) -> None:
        """Get all the inputs from all the notebooks."""
        self.get_process_from_notebooks('load')

    @log_operation('getting outputs from all notebooks')
    def get_outputs(self) -> None:
        """Get all the outputs from all the notebooks."""
        self.get_process_from_notebooks('getOutputs')

    @log_operation('printing irrep in all notebooks')
    def print_irrep(self, new_sym: bool = False) -> None:
        """Change all the entries/combos that have irrep info in all the notebooks."""
        self.get_process_from_notebooks('print_irrep', new_sym)

    @log_operation('reseting all notebooks')
    def reset_notebooks(self) -> None:
        """Reset all notebooks to default values."""
        self.get_process_from_notebooks('reset')

    @log_operation('reloading all input/output')
    def reload(self) -> None:
        """Reload all the inputs/outputs of the GUI."""
        self.reset_notebooks()
        self.get_inputs()

    @log_operation('copying template')
    def copy_template(self) -> None:
        """Copy a template directory to the running directory."""
        if not self.running_directory:
            directory_popup()
            return

        if not overwrite_warning_popup():
            return

        template_path = self.get_running_dir(
            input_path=None,
            new_path=True,
            initial_dir=self.astra_gui_path.parent / 'tests',
        )
        if not template_path:
            return

        self.erase()
        for folder in ['QC', 'store']:
            if self.ssh_client:
                if self.ssh_client.path_exists(Path(folder)):
                    self.ssh_client.run_remote_command(f'rm -rf {self.running_directory / folder}')
            elif Path(folder).is_dir():
                shutil.rmtree(folder)

        if self.ssh_client:
            self.ssh_client.run_remote_command(f'mv -r {template_path} {self.running_directory}')
        else:
            shutil.copytree(template_path, self.running_directory, dirs_exist_ok=True)

        self.get_inputs()
        self.get_outputs()


def main() -> None:
    """Run main function to run the ASTRA GUI application."""
    parser = argparse.ArgumentParser()
    parser.add_argument('path', nargs='?', default=None, action='store', help='Path to run the GUI on (optional)')
    logging_group = parser.add_mutually_exclusive_group()
    logging_group.add_argument('-db', '--debug', action='store_true', help='Enable debug logging output')
    logging_group.add_argument('-v', '--verbose', action='store_true', help='Show info level logging output')
    logging_group.add_argument('-q', '--quiet', action='store_true', help='Only show error logging output')
    parser.add_argument('-ssh', action='store_true', help='Run the GUI over ssh')
    parser.add_argument('-t', '--test', nargs='?', const='all', help='Run all tests if no index is given')

    create_cc = parser.add_argument_group(title='Create Close Coupling pages')
    create_cc.add_argument('-m', '--molecule', action='store_true')
    create_cc.add_argument('-d', '--dalton', action='store_true')
    create_cc.add_argument('-l', '--lucia', action='store_true')
    create_cc.add_argument('-c', '--closecoupling', action='store_true')
    create_cc.add_argument('-b', '--bsplines', action='store_true')

    time_independent = parser.add_argument_group('Time Independent pages')
    time_independent.add_argument('-struc', '--structural', action='store_true')
    time_independent.add_argument('-scatt', '--scattering', action='store_true')
    time_independent.add_argument('-pad', '--pad', action='store_true')

    time_dependent = parser.add_argument_group('Time Dependent pages')
    time_dependent.add_argument('-p', '--pulse', action='store_true')

    args = parser.parse_args()

    setup_logger(debug=args.debug, verbose=args.verbose, quiet=args.quiet)

    astra = Astra(args)
    astra.mainloop()


if __name__ == '__main__':
    main()
