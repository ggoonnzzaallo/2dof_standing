"""Build/upload the robot from VS Code or a terminal, without Arduino IDE.

Tools and downloads stay in .tools/; generated firmware stays in build/.
"""
import argparse
import json
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / '.tools' / 'arduino'
CONFIG = TOOLS / 'arduino-cli.yaml'
CLI = TOOLS / 'arduino-cli'
PYTHON = TOOLS / 'python' / 'bin' / 'python'
UPLOADER = TOOLS / 'nrfutil'
CORE_VERSION = '1.1.13'
CLI_VERSION = '1.5.1'
FQBN = 'Seeeduino:nrf52:xiaonRF52840Sense'
CORE = TOOLS / 'data' / 'packages' / 'Seeeduino' / 'hardware' / 'nrf52' / CORE_VERSION
NATIVE = TOOLS / 'arm-gnu-toolchain-13.2.Rel1-darwin-arm64-arm-none-eabi'
CTAGS = TOOLS / 'ctags-5.8-arduino11'
BUILD = ROOT / 'build' / 'servo_center'
INDEX = 'https://files.seeedstudio.com/arduino/package_seeeduino_boards_index.json'


def run(args, **kwargs):
    kwargs.setdefault('check', True)
    kwargs.setdefault('cwd', ROOT)
    return subprocess.run([str(a) for a in args], **kwargs)


def download(url, destination):
    print(f'Downloading {destination.name} ...', flush=True)
    partial = destination.with_suffix(destination.suffix + '.partial')
    with urllib.request.urlopen(url, timeout=120) as response, partial.open('wb') as output:
        shutil.copyfileobj(response, output)
    partial.replace(destination)


def write_config():
    TOOLS.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps({
        'board_manager': {'additional_urls': [INDEX]},
        'directories': {key: str(TOOLS / name) for key, name in
                        [('data', 'data'), ('downloads', 'downloads'), ('user', 'user')]},
    }, indent=2))


def arduino(*args, **kwargs):
    return run([CLI, '--config-file', CONFIG, *args], **kwargs)


def setup_tools():
    if platform.system() != 'Darwin':
        raise SystemExit('This setup currently targets macOS. The sketch itself is portable.')
    write_config()
    if not CLI.exists():
        arch = 'ARM64' if platform.machine() == 'arm64' else '64bit'
        asset = f'arduino-cli_{CLI_VERSION}_macOS_{arch}.tar.gz'
        archive = TOOLS / 'cli.tar.gz'
        download(f'https://github.com/arduino/arduino-cli/releases/download/v{CLI_VERSION}/{asset}', archive)
        with tarfile.open(archive) as package:
            package.extract(package.getmember('arduino-cli'), TOOLS, filter='data')
    if not CORE.exists():
        arduino('core', 'update-index')
        arduino('core', 'install', f'Seeeduino:nrf52@{CORE_VERSION}')
    if platform.machine() == 'arm64' and not NATIVE.exists():
        archive = TOOLS / 'native-gcc.tar.xz'
        download('https://developer.arm.com/-/media/Files/downloads/gnu/13.2.Rel1/binrel/'
                 'arm-gnu-toolchain-13.2.Rel1-darwin-arm64-arm-none-eabi.tar.xz', archive)
        with tarfile.open(archive) as package:
            package.extractall(TOOLS, filter='data')
    if platform.machine() == 'arm64':
        if not (CTAGS / 'ctags').exists():
            archive = TOOLS / 'ctags-source.tar.gz'
            download('https://github.com/arduino/ctags/archive/refs/tags/5.8-arduino11.tar.gz', archive)
            with tarfile.open(archive) as package:
                package.extractall(TOOLS, filter='data')
            # The old utility's reserved macro collides with current macOS SDK
            # headers. Rename it only in this project's downloaded source cache.
            for source in list(CTAGS.glob('*.h')) + list(CTAGS.glob('*.c')):
                source.write_bytes(source.read_bytes().replace(b'__unused__', b'CTAGS_UNUSED'))
            run(['sh', 'configure'], cwd=CTAGS)
            run(['make', '-j4', 'CFLAGS=-O2 -Wno-error=implicit-function-declaration '
                 '-Wno-error=int-conversion'], cwd=CTAGS)
        builtin = TOOLS / 'data/packages/builtin/tools/ctags/5.8-arduino11/ctags'
        shutil.copy2(CTAGS / 'ctags', builtin)
    if not PYTHON.exists():
        interpreter = shutil.which('python3.12') or sys.executable
        run([interpreter, '-m', 'venv', TOOLS / 'python'])
    if run([PYTHON, '-c', 'import nordicsemi, serial, pkg_resources'],
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
               check=False).returncode:
        run([PYTHON, '-m', 'pip', 'install', '--cache-dir', TOOLS / 'pip-cache',
             'setuptools<81', 'adafruit-nrfutil==0.5.3.post16'])
    UPLOADER.write_text('#!/bin/sh\nexec ' + shlex.quote(str(PYTHON)) + ' -m nordicsemi "$@"\n')
    UPLOADER.chmod(0o755)
    print('Local XIAO toolchain ready. No Arduino IDE or VS Code extension required.')


def require_tools():
    if not all(p.exists() for p in (CLI, CONFIG, CORE, PYTHON, UPLOADER)):
        raise SystemExit('First run: python3 scripts/robot.py setup')


def build(sketch='servo_center'):
    require_tools()
    if sketch not in ('servo_center', 'policy_probe', 'imu_bench', 'policy_shadow', 'servo_calibration'):
        raise ValueError('Unknown project sketch.')
    build_path = ROOT / 'build' / sketch
    props = {'tools.nrfutil.cmd': str(UPLOADER),
             'tools.nrfutil.cmd.macosx': str(UPLOADER)}
    if sketch in ('policy_shadow', 'servo_calibration'):
        # Preserve finite-value guards in the estimator (the core defaults to Ofast).
        props['compiler.optimization_flag'] = '-O2'
    if platform.system() == 'Darwin' and platform.machine() == 'arm64':
        props['compiler.path'] = str(NATIVE / 'bin') + '/'
    # Seeed 1.1.13 leaves the sketch include path unquoted. Our project folder
    # contains spaces, so correct that through CLI properties, not package edits.
    settings = dict(line.split('=', 1) for line in (CORE / 'platform.txt').read_text().splitlines()
                    if '=' in line and not line.lstrip().startswith('#'))
    for key in ('compiler.c.flags', 'compiler.cpp.flags', 'compiler.S.flags'):
        props[key] = settings[key].replace('-I{build.source.path}', '"-I{build.source.path}"')
    props['recipe.objcopy.uf2.pattern'] = (
        f'"{PYTHON}" "{{runtime.platform.path}}/tools/uf2conv/uf2conv.py" '
        '-f 0xADA52840 -c -o "{build.path}/{build.project_name}.uf2" '
        '"{build.path}/{build.project_name}.hex"')
    args = ['compile', '--jobs', '1', '--fqbn', FQBN, '--build-path', str(build_path)]
    for key, value in props.items():
        args.extend(['--build-property', f'{key}={value}'])
    arduino(*args, str(ROOT / 'firmware' / sketch))


def board_ports():
    require_tools()
    result = arduino('board', 'list', '--json', capture_output=True, text=True)
    return json.loads(result.stdout).get('detected_ports', [])


def find_port(requested=None):
    matching = [item['port']['address'] for item in board_ports()
                if any(board.get('fqbn') == FQBN for board in item.get('matching_boards', []))]
    if requested:
        if requested not in matching:
            raise SystemExit(f'{requested} is not identified as the XIAO nRF52840 Sense.')
        return requested
    if len(matching) != 1:
        raise SystemExit('Connect exactly one XIAO nRF52840 Sense, or specify --port after ports.')
    return matching[0]


def upload(port, sketch='servo_center'):
    selected = find_port(port)
    build(sketch)
    print(f'Uploading {sketch} firmware to {selected}', flush=True)
    result = arduino('upload', '--fqbn', FQBN, '--port', selected, '--input-dir', str(ROOT / 'build' / sketch),
            '--upload-property', f'tools.nrfutil.cmd={UPLOADER}',
            '--upload-property', f'tools.nrfutil.cmd.macosx={UPLOADER}',
            '--upload-property', f'cmd={UPLOADER}', capture_output=True, text=True)
    print(result.stdout, end='')
    print(result.stderr, end='', file=sys.stderr)
    # Adafruit-nrfutil can return exit code zero even when DFU has failed.
    # Require the uploader's positive acknowledgement, not just a zero status.
    if 'Device programmed.' not in result.stdout or 'Failed to upgrade target.' in result.stdout:
        raise SystemExit('Upload was NOT confirmed. Double-press reset, list ports and retry.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['setup', 'build', 'build-probe', 'build-imu', 'build-shadow', 'build-calibration', 'ports', 'upload', 'upload-imu', 'upload-shadow', 'upload-calibration', 'monitor', 'check', 'test'])
    parser.add_argument('--port', help='Explicit XIAO serial port; auto-detects if exactly one is connected')
    args = parser.parse_args()
    if args.action == 'setup':
        setup_tools()
    elif args.action == 'build':
        build()
    elif args.action == 'build-probe':
        build('policy_probe')
    elif args.action == 'build-imu':
        build('imu_bench')
    elif args.action == 'build-shadow':
        build('policy_shadow')
    elif args.action == 'build-calibration':
        build('servo_calibration')
    elif args.action == 'ports':
        print(json.dumps(board_ports(), indent=2))
    elif args.action == 'upload':
        upload(args.port)
    elif args.action == 'upload-imu':
        upload(args.port, 'imu_bench')
    elif args.action == 'upload-shadow':
        upload(args.port, 'policy_shadow')
    elif args.action == 'upload-calibration':
        upload(args.port, 'servo_calibration')
    elif args.action == 'monitor':
        run([PYTHON, '-m', 'serial.tools.miniterm', find_port(args.port), '115200', '--eol', 'LF', '--echo'])
    elif args.action == 'check':
        # Both commands disarm. Request help explicitly because a USB host can
        # assert DTR before we open the port and miss the initial version banner.
        code = ('import serial,time,sys; '
                's=serial.Serial(sys.argv[1],115200,timeout=0.2); '
                'time.sleep(1); s.write(bytes([104,101,108,112,10,111,102,102,10])); '
                'time.sleep(0.5); data=s.read(8192).decode(errors="replace"); s.close(); '
                'print(data); '
                'sys.exit(0 if "ROBOT SERVO CENTER 0.10" in data and "OFF." in data.splitlines() else 1)')
        run([PYTHON, '-c', code, find_port(args.port)])
    else:
        run([sys.executable, ROOT / 'firmware' / 'test_servo_center.py'])
        run([sys.executable, ROOT / 'firmware' / 'test_fine_servo.py'])
        run([sys.executable, ROOT / 'firmware' / 'test_imu_bench.py'])
        run([sys.executable, ROOT / 'firmware' / 'test_imu_bus.py'])
        run([sys.executable, ROOT / 'firmware' / 'test_imu_logger.py'])
        run([sys.executable, ROOT / 'firmware' / 'test_gravity_filter.py'])
        run([sys.executable, ROOT / 'firmware' / 'test_policy_shadow.py'])
        run([sys.executable, ROOT / 'firmware' / 'test_servo_calibration.py'])


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)
