from cx_Freeze import setup, Executable

import sys

# collectors_files=["builtin","conf","etc","lib","__init__.py"]
files=["runner.conf","util.py"]
# for path in collectors_files:
#     c_files.append("collectors/"+path)
# c_files.extend(files)
buildOptions = dict(include_files=files)

build_exe_options = {"packages": ["collectors"],"include_files":files}

executables = [
    Executable('runner.py'),
    Executable('collector_mgr.py')
]

setup(name='agent',
      version='0.1',
      description='Sample cx_Freeze script',
      executables=executables,
      options=dict(build_exe=build_exe_options),
      )
