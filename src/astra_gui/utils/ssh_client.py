import logging
import stat  # For checking file types (S_ISDIR)
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from types import TracebackType
from typing import Optional

import paramiko
from logger_module import log_operation

logger = logging.getLogger(__name__)


class SftpContext:
    """Context manager for sftp object."""

    def __init__(self, ssh_client: paramiko.SSHClient) -> None:
        self._ssh_client = ssh_client
        self._stfp = None

    def __enter__(self) -> paramiko.SFTPClient:
        try:
            self._sftp = self._ssh_client.open_sftp()
        except (paramiko.SSHException, OSError) as e:
            # Common errors: Permission denied, No such file or directory (if parent dir missing)
            logger.error('SFTP error on entry: %s', e)
            raise
        else:
            return self._sftp

    def __exit__(
        self,
        _exc_type: Optional[type[BaseException]],
        _exc: Optional[BaseException],
        _exc_tb: Optional[TracebackType],
    ) -> None:
        if self._sftp:
            self._sftp.close()


class SshClient:
    def __init__(self, root: tk.Tk, input_file: Path) -> None:
        self.root = root
        self.input_file = input_file
        self.host_name = ''
        self.username = ''
        self.client = None

        self.load()

        self.home_path = self._get_home_path()

    def _get_home_path(self) -> Optional[str]:
        if not self.client:
            logger.error('No ssh client')
            return None

        with SftpContext(self.client) as sftp:
            # Get the absolute path of the remote home directory
            return sftp.normalize('.')

    def load(self) -> None:
        if not self.input_file.is_file():
            return

        with self.input_file.open('r') as f:
            self.host_name = f.read().split('\n')[0]

        self._ssh_setup()

    def save(self, host_name: str) -> None:
        if not host_name:
            messagebox.showerror('Missing string!', "'Host name' was not given.")
            return

        self.host_name = host_name

        with self.input_file.open('w') as f:
            f.write(host_name)

        self._ssh_setup()

    @log_operation('SSH setup')
    def _ssh_setup(self) -> None:
        ssh_config_path = Path('~/.ssh/config').expanduser()
        ssh_config = paramiko.SSHConfig()
        # Handle case where config file might not exist
        if ssh_config_path.is_file():
            with ssh_config_path.open() as f:
                ssh_config.parse(f)
        else:
            logger.error('Warning: SSH config file not found at %s', ssh_config_path)
            return

        host_config = ssh_config.lookup(self.host_name)

        if not host_config:
            logger.error('Host not found in ssh config file.')
            return

        hostname = host_config.get('hostname')
        port = int(host_config.get('port', 22))
        self.username = host_config.get('user')  # Will be None if not found
        identity_file_list = host_config.get('identityfile', [])  # Returns a list
        identity_file = identity_file_list[0] if identity_file_list else None

        # Prompt for username if not found in config
        if not self.username:
            logger.error('Username is required.')
            return

        if not identity_file:
            logger.error('Identity file specified but not found.')
            return

        identity_file = Path(identity_file).expanduser()

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        logger.info(
            'Attempting to connect to %s:%s as %s...',
            hostname,
            port,
            self.username,
        )
        # Add error handling for connection args
        connect_args = {
            'hostname': hostname,
            'port': port,
            'username': self.username,
            'key_filename': str(identity_file),
        }

        try:
            self.client.connect(**connect_args, timeout=3)  # Add timeout
        except paramiko.AuthenticationException:
            logger.error(
                'SSH authentication failed for %s@%s.\nCheck credentials/keys.',
                hostname,
                self.username,
            )
        except TimeoutError:
            logger.error('SSH authentication timeout.')
        except paramiko.SSHException as e:
            logger.error('Could not establish SSH connection to %s: %s', hostname, e)

        logger.info('Connected to %s', hostname)

    def browse_remote(
        self,
        initial_dir: Optional[Path] = None,
        title: Optional[str] = None,
        dirs: bool = True,
        files: bool = False,
    ) -> Optional[str]:
        if not self.client:
            return None

        with SftpContext(self.client) as sftp:
            if not initial_dir:
                # Try to get remote home directory as starting point
                try:
                    start_dir = sftp.normalize('.')
                except paramiko.SFTPError:
                    start_dir = '/'  # Fallback to root if home dir fails
            else:
                start_dir = str(initial_dir)

            dialog = RemoteFileDialog(
                self.root,
                sftp,
                initial_dir=start_dir,
                title=title,
                show_dirs=dirs,
                show_files=files,
            )
            return dialog.selected_path

    def read_from_file(self, remote_path: Path, decode: bool = True) -> str | bytes:
        """Read the content of a text file from the remote server."""
        if not self.client:
            logger.error('No ssh client setuped.')
            return ''

        content = ''
        with SftpContext(self.client) as sftp:
            try:
                with sftp.open(str(remote_path), 'r') as remote_file:
                    content = remote_file.read()
                    if decode:
                        content = content.decode('utf-8')
            except FileNotFoundError:
                logger.error('Remote file not found: %s', remote_path)
                return ''
            else:
                return content

    def write_to_file(self, remote_path: Path, content: str) -> None:
        """
        Write content to a file on the remote server. Overwrites if the file exists.

        Args:
            client: An active Paramiko SSHClient object connected to the target server.
            remote_path: The absolute path to the file on the remote server.
                         The parent directory must exist.
            content: The string or bytes content to write to the file.
                     If string, it will be encoded using the specified encoding.
            encoding: The text encoding to use if content is a string (defaults to utf-8).

        """
        if not self.client:
            logger.error('No ssh client setuped.')
            return

        with SftpContext(self.client) as sftp:
            try:
                sftp.stat(str(remote_path.parent))
                with sftp.open(str(remote_path), 'w') as remote_file:
                    remote_file.write(content)
            except FileNotFoundError:
                logger.error('Remote directory %s does not exist.', remote_path.parent)

    def path_exists(self, remote_path: Path) -> bool:
        """
        Check if a file or directory exists at the specified path on the remote server.

        Args:
            remote_path: The absolute path to check on the remote server.

        Returns:
            True if the path exists (can be a file or directory), False otherwise
            (including cases of permission errors preventing stat).

        """
        if not self.client:
            logger.error('No ssh client')
            return False

        with SftpContext(self.client) as sftp:
            try:
                sftp.stat(str(remote_path))
            except FileNotFoundError:
                return False
            else:
                return True

    def run_remote_command(self, command: str) -> tuple[str, str, int]:
        """
        Execute a command on the remote server via the SSH client.

        Args:
            command: The command string to execute.

        Returns:
            A tuple containing:
                - stdout output (decoded string)
                - stderr output (decoded string)
                - exit status code (integer)

        """
        if not self.client:
            logger.error('No ssh client.')
            return '', '', -1
        try:
            _, stdout, stderr = self.client.exec_command(
                command,
                timeout=15,
            )  # Add a timeout
            # It's important to read stdout/stderr before getting exit status
            stdout_output = stdout.read().decode().strip()
            stderr_output = stderr.read().decode().strip()
            exit_status = stdout.channel.recv_exit_status()  # Blocks until command finishes
            if stderr_output:
                logger.warning(
                    "Command '%s' produced stderr: %s",
                    command,
                    stderr_output,
                )

        except paramiko.SSHException as e:
            logger.error("SSH error executing command '%s': %s", command, e)
            return '', str(e), -1  # Indicate failure
        else:
            return stdout_output, stderr_output, exit_status


# --- Custom Remote Directory Browser ---
class RemoteFileDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Tk,
        sftp_client: paramiko.SFTPClient,
        initial_dir: str = '.',
        title: Optional[str] = None,
        show_dirs: bool = True,
        show_files: bool = False,
    ) -> None:
        super().__init__(parent)
        self.sftp = sftp_client
        self.selected_path = None
        self.show_hidden = False  # State for showing hidden dirs
        self.show_dirs = show_dirs
        self.show_files = show_files

        self.current_path = self._resolve_path(initial_dir)  # Store absolute path

        if not title:
            self.title('Browse Remote Directory')
        else:
            self.title(title)

        self.geometry('550x450')
        self.grab_set()
        self.transient(parent)

        # Frame for path display and Up button
        path_frame = ttk.Frame(self)
        path_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(path_frame, text='Up', command=self.go_up).pack(side=tk.LEFT)
        self.path_label = ttk.Label(
            path_frame,
            text=self.current_path,
            anchor=tk.W,
            relief=tk.SUNKEN,
            padding=(2, 2),
        )
        self.path_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # Frame for listbox and scrollbar
        list_frame = ttk.Frame(self)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.scrollbar_x = ttk.Scrollbar(
            list_frame,
            orient=tk.HORIZONTAL,
        )  # Add horizontal scrollbar

        self.listbox = tk.Listbox(
            list_frame,
            yscrollcommand=self.scrollbar.set,
            xscrollcommand=self.scrollbar_x.set,  # Link horizontal scrollbar
            selectmode=tk.SINGLE,
            font=('monospace', 10),  # Monospace font helps alignment
        )

        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scrollbar_x.pack(
            side=tk.BOTTOM,
            fill=tk.X,
        )  # Pack horizontal scrollbar at the bottom
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.scrollbar.config(command=self.listbox.yview)
        self.scrollbar_x.config(
            command=self.listbox.xview,
        )  # Configure horizontal scrollbar command

        self.listbox.bind('<Double-Button-1>', self.on_double_click)
        self.listbox.bind('<Return>', self.on_double_click)

        # Frame for action buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=5, pady=(0, 5))  # Adjusted padding

        # <<<--- Add Toggle Hidden Button
        self.toggle_hidden_button = ttk.Button(
            button_frame,
            text='Show Hidden',
            command=self.toggle_hidden,
        )
        self.toggle_hidden_button.pack(side=tk.LEFT, padx=(0, 5))  # Pack on the left

        self.new_folder_button = ttk.Button(
            button_frame,
            text='New Folder',
            command=self.create_new_folder,
        )
        self.new_folder_button.pack(
            side=tk.LEFT,
            padx=(0, 5),
        )  # Add it next to toggle hidden

        ttk.Button(button_frame, text='Cancel', command=self.destroy).pack(
            side=tk.RIGHT,
            padx=(2, 0),
        )
        ttk.Button(button_frame, text='Select', command=self.select_action).pack(
            side=tk.RIGHT,
            padx=2,
        )

        self.update_list()
        self.protocol('WM_DELETE_WINDOW', self.destroy)
        self.wait_window(self)

    def create_new_folder(self) -> None:
        """Prompts user for a new folder name and creates it in the current directory."""
        new_name = simpledialog.askstring(
            'New Folder',
            f'Enter name for new folder in:\n{self.current_path}',
            parent=self,  # Make dialog appear over this window
        )

        if not new_name:  # User cancelled or entered empty string
            return

        # Basic validation (optional but recommended)
        if '/' in new_name or '\\' in new_name or not new_name.strip():
            messagebox.showerror(
                'Invalid Name',
                'Folder name cannot be empty or contain slashes.',
                parent=self,
            )
            return

        new_folder_path = str(Path(self.current_path) / new_name.strip())

        try:
            self.sftp.mkdir(new_folder_path)
            # Refresh the listbox to show the new folder
            self.update_list()
        except OSError as e:
            # Common errors: Permission denied, File exists
            logger.warning('Failed to create directory %s: %s', new_folder_path, e)

    def _resolve_path(self, path: str) -> str:
        """Get absolute path using sftp.normalize."""
        try:
            return self.sftp.normalize(path)
        except OSError as e:
            logger.error("Could not resolve path '%s': %s", path, e)

        return ''

    def toggle_hidden(self) -> None:
        """Toggle the display of hidden files/folders."""
        self.show_hidden = not self.show_hidden
        button_text = 'Hide Hidden' if self.show_hidden else 'Show Hidden'
        self.toggle_hidden_button.config(text=button_text)
        self.update_list()  # Refresh the listbox content

    def update_list(self) -> None:
        self.listbox.delete(0, tk.END)
        self.path_label.config(text=self.current_path)
        try:
            items_raw = self.sftp.listdir_attr(self.current_path)

            # Filter hidden files/dirs if necessary
            if not self.show_hidden:
                items = [item for item in items_raw if not item.filename.startswith('.')]
            else:
                items = items_raw  # Show all items

            # Sort directories first, then files, case-insensitively
            items.sort(key=lambda attr: (not stat.S_ISDIR(attr.st_mode), attr.filename.lower()))  # pyright: ignore[reportArgumentType]

            self.listbox.insert(tk.END, '[ .. ]')  # Parent directory entry

            for item in items:
                if item.filename in {'.', '..'}:  # Skip . and .. explicitly
                    continue
                if not self.show_files and stat.S_ISREG(item.st_mode):  # pyright: ignore[reportArgumentType]
                    continue

                if not self.show_dirs and stat.S_ISDIR(item.st_mode):  # pyright: ignore[reportArgumentType]
                    continue

                display_name = f'{item.filename}'  # Simpler display
                self.listbox.insert(tk.END, display_name)

        except OSError as e:
            logger.error("Cannot list directory '%s':\n%s", self.current_path, e)
        except Exception as e:  # noqa: BLE001
            logger.error('An unexpected error occurred during listing:\n%s', e)

    def go_up(self) -> None:
        # Ensure we don't try to go above root ('/')
        parent_path = str(Path(self.current_path).parent)
        if parent_path != self.current_path:  # Avoid getting stuck at '/'
            try:
                resolved_parent = self._resolve_path(parent_path)
                # Double-check if path actually changed after resolving potential symlinks etc.
                if resolved_parent != self.current_path:
                    self.current_path = resolved_parent
                    self.update_list()
            except OSError as e:
                logger.error('Cannot navigate up:\n%s', e)

    def on_double_click(self, _event: Optional[tk.Event] = None) -> None:
        selection_indices = self.listbox.curselection()
        if not selection_indices:
            return

        selected_item_display = self.listbox.get(selection_indices[0])

        if selected_item_display == '[ .. ]':
            self.go_up()
            return

        # Check if it's marked as a directory
        new_path = str(Path(self.current_path) / selected_item_display)
        try:
            # Verify it's still a directory before navigating
            stat_info = self.sftp.stat(new_path)
            if stat.S_ISDIR(stat_info.st_mode):  # pyright: ignore[reportArgumentType]
                self.current_path = self._resolve_path(new_path)  # Resolve the new path
                self.update_list()
            else:
                logger.error("'%s' is no longer a directory.", selected_item_display)
        except OSError as e:
            logger.error("Cannot access '%s':\n%s", new_path, e)
        # else: Item is a file "[F]", do nothing on double-click for directory selection

    def select_action(self) -> None:
        """Set the selected_path based on highlight or current path and closes."""
        selection_indices = self.listbox.curselection()
        path_to_select = self.current_path  # Default to current directory

        if selection_indices:
            selected_item_display = self.listbox.get(selection_indices[0])

            # Check if it's a directory entry (and not the '..' entry)
            if selected_item_display != '[ .. ]':
                try:
                    # Extract directory name
                    potential_path = str(
                        Path(self.current_path) / selected_item_display,
                    )
                    # Resolve/normalize the path to be sure
                    path_to_select = self._resolve_path(potential_path)
                except (OSError, RuntimeError) as e:
                    logger.error('Could not resolve selected directory path:\n%s', e)

        # If no selection or selected item wasn't a directory, path_to_select remains self.current_path
        self.selected_path = path_to_select
        self.destroy()  # Close the dialog


if __name__ == '__main__':
    # --- Example Tkinter Root Window ---
    root = tk.Tk()
    root.title('SSH Remote Browser (majorana)')
    root.geometry('400x200')

    # Improve button styling
    style = ttk.Style()
    style.configure('TButton', padding=6, relief='flat', background='#ccc')

    ssh_client = SshClient(root, Path('.ssh_host'))

    browse_button = ttk.Button(root, text='Browse Remote Folder...', command=ssh_client.browse_remote, style='TButton')
    browse_button.pack(pady=20, padx=20, fill=tk.X)

    result_label = ttk.Label(
        root,
        text='Selected: None',
        anchor=tk.W,
        relief=tk.SUNKEN,
        padding=5,
    )
    result_label.pack(pady=10, padx=20, fill=tk.X)

    root.mainloop()
