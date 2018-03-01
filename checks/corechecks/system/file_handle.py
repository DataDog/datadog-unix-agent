from config import config
from checks import AgentCheck
from utils.platform import Platform


class FileHandle(AgentCheck):

    def check(self):

        if not Platform.is_linux():
            return False

        try:
            proc_location = config.get('procfs_path', '/proc').rstrip('/')
            proc_fh = "{}/sys/fs/file-nr".format(proc_location)
            with open(proc_fh, 'r') as file_handle:
                handle_contents = file_handle.readline()
        except Exception:
            self.log.exception("Cannot extract system file handles stats")
            return

        handle_metrics = handle_contents.split()

        # https://www.kernel.org/doc/Documentation/sysctl/fs.txt
        allocated_fh = float(handle_metrics[0])
        allocated_unused_fh = float(handle_metrics[1])
        max_fh = float(handle_metrics[2])

        fh_in_use = (allocated_fh - allocated_unused_fh) / max_fh

        self.gauge('system.fs.file_handles.in_use', float(fh_in_use))
