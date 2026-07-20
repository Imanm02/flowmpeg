# Install Flowmpeg and FFmpeg

Flowmpeg is a Python package. FFmpeg and FFprobe are separate programs that do
the media work. A working installation needs all three commands:

```console
python --version
ffmpeg -version
ffprobe -version
```

Flowmpeg supports Python 3.10 or newer. Its Python package has no required
runtime dependencies.

## Quick start

Install the current repository version:

```console
python -m pip install "git+https://github.com/Imanm02/flowmpeg.git"
flowmpeg --version
flowmpeg setup
```

`flowmpeg setup` checks both media tools and reports a package manager command
when one is available. The default check is read-only. Its final line says
`No changes were made`.

Run the full capability check after both tools are found:

```console
flowmpeg doctor
```

`doctor` checks a selected set of filters, encoders, and muxers used by common
Flowmpeg jobs. Use JSON in scripts:

```console
flowmpeg doctor --json
flowmpeg setup --json
```

Both reports include a top-level `schema_version` for scripts that validate
their expected object shape.

Require one group in CI when a job depends on it:

```console
flowmpeg doctor --require web-video
flowmpeg doctor --require audiogram --json
```

Without `--require`, limited optional groups do not change the exit code. A
requested group that is limited or unknown returns exit code 3.

## Let Flowmpeg run the package manager

Installation is opt-in:

```console
flowmpeg setup --install
```

Flowmpeg prints every command first and asks:

```text
Run these package manager commands? [y/N]
```

For an unattended terminal, confirmation must be explicit:

```console
flowmpeg setup --install --yes
```

Each package manager command has a ten-minute limit by default. Set a shorter
or longer positive limit when needed:

```console
flowmpeg setup --install --yes --install-timeout 900
```

This action can install the `ffmpeg` package through an existing package
manager. It does not install a package manager, add a package repository,
download an archive itself, or change `PATH`. Commands run as argument lists
with `shell=False`.

| System | Detected manager | Package command |
| --- | --- | --- |
| Windows | WinGet | `winget install --id Gyan.FFmpeg -e --source winget` |
| Windows | Chocolatey | `choco install ffmpeg -y` |
| Windows | Scoop | `scoop install ffmpeg` |
| macOS | Homebrew | `brew install ffmpeg` |
| Debian or Ubuntu | APT | `apt-get update`, then `apt-get install -y ffmpeg` |
| Arch Linux | pacman | `pacman -S --needed --noconfirm ffmpeg` |
| Alpine Linux | apk | `apk add ffmpeg` |
| Linux with Homebrew | Homebrew | `brew install ffmpeg` |

Linux system managers are prefixed with `sudo` when it is available and the
current process is not root.

Flowmpeg does not configure RPM Fusion on Fedora or Packman on openSUSE. Codec
repository choices affect the whole system, so follow the distribution's own
instructions for those systems.

## Windows

The shortest checked path is:

```console
flowmpeg setup
flowmpeg setup --install
```

The WinGet command uses an exact package ID and source:

```console
winget install --id Gyan.FFmpeg -e --source winget
```

Microsoft documents `--id`, `-e`, and `--source` as the way to select an exact
package from one source in the
[WinGet install command reference](https://learn.microsoft.com/en-us/windows/package-manager/winget/install).

If WinGet reports success but the current terminal cannot find FFmpeg, close
the terminal, open a new one, and run:

```console
where ffmpeg
where ffprobe
flowmpeg doctor
```

For a manual install, use a Windows build linked from the
[official FFmpeg download page](https://ffmpeg.org/download.html). Add the
build's `bin` folder to `PATH`, not the parent archive folder.

## macOS

With Homebrew installed:

```console
brew install ffmpeg
flowmpeg doctor
```

The command comes from the
[Homebrew ffmpeg formula](https://formulae.brew.sh/formula/ffmpeg).

If the shell cannot see Homebrew after installation, follow Homebrew's printed
shell setup instruction, open a new terminal, and rerun `flowmpeg doctor`.

## Debian and Ubuntu

```console
sudo apt-get update
sudo apt-get install -y ffmpeg
flowmpeg doctor
```

The distribution package normally includes both `ffmpeg` and `ffprobe`.
Package versions depend on the selected distribution release and repositories.

## Arch Linux

```console
sudo pacman -S --needed ffmpeg
flowmpeg doctor
```

## Alpine Linux

```console
sudo apk add ffmpeg
flowmpeg doctor
```

## Containers and CI

Install FFmpeg in the image or job before installing Flowmpeg. A Debian-based
container can use:

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install "git+https://github.com/Imanm02/flowmpeg.git"
```

Then fail the build early if required tools are absent:

```console
flowmpeg doctor --json
```

`doctor` returns exit code 3 when FFmpeg or FFprobe is unavailable. Missing
optional capabilities are reported as limited feature groups without changing
the exit code.

## Use a custom executable path

Every editing command accepts custom FFmpeg and FFprobe paths:

```console
flowmpeg convert input.mov -o output.mp4 --ffmpeg C:\tools\ffmpeg\bin\ffmpeg.exe --ffprobe C:\tools\ffmpeg\bin\ffprobe.exe
```

Probe accepts `--ffprobe`:

```console
flowmpeg probe input.mp4 --ffprobe C:\tools\ffmpeg\bin\ffprobe.exe
```

Doctor can check both custom paths:

```console
flowmpeg doctor --ffmpeg C:\tools\ffmpeg\bin\ffmpeg.exe --ffprobe C:\tools\ffmpeg\bin\ffprobe.exe
```

Setup can perform the same read-only check:

```console
flowmpeg setup --ffmpeg C:\tools\ffmpeg\bin\ffmpeg.exe --ffprobe C:\tools\ffmpeg\bin\ffprobe.exe
```

Custom setup paths are for checking an existing installation. They cannot be
combined with `--install`, which installs the package manager's default tools.

Python plans accept the executable at run time:

```python
from flowmpeg import shortcuts as ff

ff.transcode("input.mov", "output.mp4").run(
    ffmpeg=r"C:\tools\ffmpeg\bin\ffmpeg.exe"
)
```

## Understand setup statuses

| Status | Meaning | First check |
| --- | --- | --- |
| `ready` | The executable returned its version | Run `flowmpeg doctor` |
| `missing` | The executable was not found on `PATH` | Open a new terminal or install FFmpeg |
| `permission-denied` | The path exists but cannot be executed | Check file and security permissions |
| `timeout` | The version command did not finish in time | Increase `--timeout` and test the executable directly |
| `failed` | The executable started and returned an error | Run its `-version` command directly |
| `unusable` | The operating system could not start the file | Check architecture and file integrity |

Examples:

```console
flowmpeg setup --timeout 30
flowmpeg doctor --timeout 30
ffmpeg -version
ffprobe -version
```

The [error guide](errors.md) covers Flowmpeg identifiers and FFmpeg failures.
