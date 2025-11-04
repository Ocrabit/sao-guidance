import os, sys, signal

class AudacityPipeline:
    def __init__(self):
        # Initialize
        if sys.platform == 'win32':
            print("pipe-test.py, running on windows")
            TONAME = '\\\\.\\pipe\\ToSrvPipe'
            FROMNAME = '\\\\.\\pipe\\FromSrvPipe'
            self.device_specific = '\r\n\0'
        else:
            print("pipe-test.py, running on linux or mac")
            TONAME = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
            FROMNAME = '/tmp/audacity_script_pipe.from.' + str(os.getuid())
            self.device_specific = '\n'

        print("Write to  \"" + TONAME +"\"")
        if not os.path.exists(TONAME):
            print(" ..does not exist.  Ensure Audacity is running with mod-script-pipe.")
            sys.exit()

        print("Read from \"" + FROMNAME +"\"")
        if not os.path.exists(FROMNAME):
            print(" ..does not exist.  Ensure Audacity is running with mod-script-pipe.")
            sys.exit()
        print("-- Both pipes exist.  Good.")

        self.to_file = open(TONAME, 'w')
        print("-- File to write to has been opened")
        self.from_file = open(FROMNAME, 'rt')
        print("-- File to read from has now been opened too\r\n")

        # Start with new proj
        self.do_command('New:')

    def send_command(self, command):
        """Send a single command."""
        self.to_file.write(command + self.device_specific)
        self.to_file.flush()

    def get_response(self):
        """Return the command response."""
        result = ''
        line = ''
        while True:
            result += line
            line = self.from_file.readline()
            if line == '\n' and len(result) > 0:
                break
        return result

    def do_command(self, command):
        """Send one command, and return the response."""
        self.send_command(command)
        response = self.get_response()
        return response

    def import_wave(self, input_path, clear=True):
        if clear:
            self.do_command("SelectAllTracks:")
            self.do_command("RemoveTracks:")
        self.do_command("Select: Track=0")
        self.do_command(f'Import2: Filename="{input_path}"')

    def export_wave(self, output_path):
        export_command = f'Export2: Filename="{output_path}"'
        self.do_command(export_command)

    def clean_audio_via_audacity(self, path_to_audio):
        def handler(signum, frame):
            raise TimeoutError("Cleaning took too long (>10s)")
        signal.signal(signal.SIGALRM, handler)
        signal.alarm(10)

        try:
            dir_path, filename = os.path.split(path_to_audio)
            out_dir = os.path.join(dir_path, "cleaned")
            os.makedirs(out_dir, exist_ok=True)
            out_file = os.path.join(out_dir, filename)

            self.import_wave(path_to_audio)
            self.export_wave(out_file)
            print("Cleaned up file: {}".format(path_to_audio))
            return out_file
        except Exception as e:
            print(f"Failed to clean audio: {e}")
            return None
        finally:
            signal.alarm(0)