"""SSH utilities for interacting with remote hosts from the GUI."""

import logging
import stat  # For checking file types (S_ISDIR)
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from types import TracebackType

import paramiko

from .config_module import get_ssh_host, set_ssh_host
from .logger_module import log_operation

logger = logging.getLogger(__name__)


class SftpContext:
    """Context manager that opens and closes an SFTP session."""

    def __init__(self, ssh_client: paramiko.SSHClient) -> None:
        """Store the SSH client that will be used to open SFTP sessions."""
        self._ssh_client = ssh_client
        self._stfp = None

    def __enter__(self) -> paramiko.SFTPClient:
        """Open and return an SFTP client, logging failures.

        Returns
        -------
        paramiko.SFTPClient
            Active SFTP client opened from the stored SSH connection.
        """
        try:
            self._sftp = self._ssh_client.open_sftp()
        except (paramiko.SSHException, OSError) as e:
            # Common errors: Permission denied, No such file or directory (if parent dir missing)
            logger.error('SFTP session failed: %s', e)
            raise
        else:
            return self._sftp

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        """Ensure the SFTP session is closed on exit."""
        if self._sftp:
            self._sftp.close()


class SshClient:
    """Wrapper around Paramiko that adds GUI-friendly helpers."""

    def __init__(self, root: tk.Tk) -> None:
        """Create a client bound to the Tk root."""
        self.root = root
        self.host_name = ''
        self.username = ''
        self.client = None

        self.load()

        self.home_path = self._get_home_path()

    def _get_home_path(self) -> str | None:
        """Return the remote home directory path if available.

        Returns
        -------
        Optional[str]
            Normalised remote home directory, or ``None`` if unavailable.
        """
        if not self.client:
            logger.warning('SSH client unavailable: cannot determine remote home path')
            return None

        with SftpContext(self.client) as sftp:
            # Get the absolute path of the remote home directory
            return sftp.normalize('.')

    def load(self) -> None:
        """Load stored SSH settings and establish a connection."""
        host = get_ssh_host()

        if not host:
            return

        self.host_name = host
        self._ssh_setup()

    def save(self, host_name: str) -> None:
        """Persist the host configuration and reconnect."""
        if not host_name:
            logger.warning('SSH config save skipped: host name missing')
            messagebox.showerror('Missing string!', "'Host name' was not given.")
            return

        logger.info('SSH config saved: host "%s"', host_name)
        self.host_name = host_name

        set_ssh_host(host_name)

        logger.debug('SSH config saved: refreshing connection after host update')
        self._ssh_setup()

    @log_operation('SSH setup')
    def _ssh_setup(self) -> None:
        """Configure the SSH client using details from ~/.ssh/config."""
        ssh_config_path = Path('~/.ssh/config').expanduser()
        ssh_config = paramiko.SSHConfig()
        # Handle case where config file might not exist
        if ssh_config_path.is_file():
            with ssh_config_path.open() as f:
                ssh_config.parse(f)
        else:
            logger.warning('SSH setup: config file not found at %s', ssh_config_path)
            return

        host_config = ssh_config.lookup(self.host_name)

        if not host_config:
            logger.error('SSH setup failed: host "%s" not found in config', self.host_name)
            return

        hostname = host_config.get('hostname')
        if not hostname:
            logger.error('SSH setup failed: hostname missing for "%s"', self.host_name)
            return

        port = int(host_config.get('port', 22))
        self.username = host_config.get('user')  # Will be None if not found
        identity_file_list = host_config.get('identityfile', [])  # Returns a list
        identity_file = identity_file_list[0] if identity_file_list else None

        # Prompt for username if not found in config
        if not self.username:
            logger.error('SSH setup failed: username missing for "%s"', self.host_name)
            return

        if not identity_file:
            logger.error('SSH setup failed: identity file missing for "%s"', self.host_name)
            return

        identity_file = Path(identity_file).expanduser()
        if not identity_file.exists():
            logger.error('SSH setup failed: identity file not found at %s', identity_file)
            return

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        logger.info(
            'SSH setup: connecting to %s:%s as %s',
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
                'SSH login failed: %s@%s (authentication)',
                self.username,
                hostname,
            )
            self.client = None
            return
        except TimeoutError:
            logger.error(
                'SSH login timed out: %s@%s',
                self.username,
                hostname,
            )
            self.client = None
            return
        except (paramiko.SSHException, OSError) as e:
            logger.error('SSH connection error: %s', e)
            self.client = None
            return

        logger.info(
            'SSH setup: connected to %s:%s as %s',
            hostname,
            port,
            self.username,
        )

    def browse_remote(
        self,
        initial_dir: Path | None = None,
        title: str | None = None,
        dirs: bool = True,
        files: bool = False,
    ) -> str | None:
        """Open a dialog for browsing the remote filesystem.

        Returns
        -------
        Optional[str]
            Selected remote path, or ``None`` if the dialog was cancelled.
        """
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
        """Read the content of a text file from the remote server.

        Returns
        -------
        str | bytes
            File contents (decoded if requested) or an empty string on failure.
        """
        if not self.client:
            logger.warning('SSH client unavailable: cannot read %s', remote_path)
            return ''

        content = ''
        with SftpContext(self.client) as sftp:
            try:
                with sftp.open(str(remote_path), 'r') as remote_file:
                    content = remote_file.read()
                    if decode:
                        content = content.decode('utf-8')
            except FileNotFoundError:
                logger.warning('Remote file missing: %s', remote_path)
                return ''
            else:
                return content

    def write_to_file(self, remote_path: Path, content: str) -> None:
        """Write `content` to the remote path, overwriting any existing file."""
        if not self.client:
            logger.warning('SSH client unavailable: cannot write %s', remote_path)
            return

        with SftpContext(self.client) as sftp:
            try:
                sftp.stat(str(remote_path.parent))
                with sftp.open(str(remote_path), 'w') as remote_file:
                    remote_file.write(content)
            except FileNotFoundError:
                logger.warning('Remote directory missing: %s', remote_path.parent)

    def path_exists(self, remote_path: Path) -> bool:
        """Return True if the given path exists on the remote host.

        Returns
        -------
        bool
            True when the remote path can be stat'ed successfully.
        """
        if not self.client:
            logger.warning('SSH client unavailable: cannot stat %s', remote_path)
            return False

        with SftpContext(self.client) as sftp:
            try:
                sftp.stat(str(remote_path))
            except FileNotFoundError:
                return False
            else:
                return True

    def run_remote_command(self, command: str) -> tuple[str, str, int]:
        """Execute `command` remotely and return stdout, stderr, and exit status.

        Returns
        -------
        tuple[str, str, int]
            Decoded stdout, stderr, and exit status of the remote command.
        """
        if not self.client:
            logger.error('SSH command failed: client not connected')
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
                logger.warning('SSH command stderr: %s -> %s', command, stderr_output)

        except paramiko.SSHException as e:
            logger.error('SSH command error: %s -> %s', command, e)
            return '', str(e), -1  # Indicate failure
        else:
            return stdout_output, stderr_output, exit_status


# --- Custom Remote Directory Browser ---
class RemoteFileDialog(tk.Toplevel):
    """Simple Tk dialog that lets the user browse directories over SFTP."""

    def __init__(
        self,
        parent: tk.Tk,
        sftp_client: paramiko.SFTPClient,
        initial_dir: str = '.',
        title: str | None = None,
        show_dirs: bool = True,
        show_files: bool = False,
    ) -> None:
        """Initialise the remote file dialog and populate the list view."""
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
            logger.warning('Remote directory creation failed: %s -> %s', new_folder_path, e)

    def _resolve_path(self, path: str) -> str:
        """Get absolute path using sftp.normalize.

        Returns
        -------
        str
            Absolute path derived from the current remote directory.
        """
        try:
            return self.sftp.normalize(path)
        except OSError as e:
            logger.warning('Remote path resolution failed: %s -> %s', path, e)

        return ''

    def toggle_hidden(self) -> None:
        """Toggle the display of hidden files/folders."""
        self.show_hidden = not self.show_hidden
        button_text = 'Hide Hidden' if self.show_hidden else 'Show Hidden'
        self.toggle_hidden_button.config(text=button_text)
        self.update_list()  # Refresh the listbox content

    def update_list(self) -> None:
        """Refresh the list of remote entries shown in the dialog."""
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
            logger.warning('Remote listing failed: %s -> %s', self.current_path, e)
        except Exception as e:  # noqa: BLE001
            logger.error('Remote listing crashed: %s', e)

    def go_up(self) -> None:
        """Navigate to the parent directory if possible."""
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
                logger.warning('Remote navigation failed: %s -> %s', parent_path, e)

    def on_double_click(self, _event: tk.Event | None = None) -> None:
        """Handle navigation when the user double-clicks an entry."""
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
                logger.warning("Remote selection skipped: '%s' is no longer a directory", selected_item_display)
        except OSError as e:
            logger.warning("Remote selection failed: '%s' -> %s", new_path, e)
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
                    logger.warning('Remote selection resolution failed: %s', e)

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

    ssh_client = SshClient(root)

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
