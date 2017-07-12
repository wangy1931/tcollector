from cx_Freeze import setup, Executable


# collectors_files=["builtin","conf","etc","lib","__init__.py"]
files=["runner.conf","lib/nssm.exe","deploy/windows/README.md","deploy/windows/windows_init.bat"]


buildOptions = dict(include_files=files)

build_exe_options = {"packages": ["collectors"],"include_files":files}

executables = [
    Executable('runner.py'),
    Executable('collector_mgr.py'),
    Executable('deploy/windows/window_deploy.py')
]

setup(name='cloudwiz-agent',
      version='0.1',
      description='collectors',
      executables=executables,
      options=dict(build_exe=build_exe_options),
      )
