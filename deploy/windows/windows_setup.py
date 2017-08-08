from cx_Freeze import setup, Executable


# collectors_files=["builtin","conf","etc","lib","__init__.py"]
files=["runner.conf",
       "collectors/",
       "logs/","runs/",
       "lib/cloudwiz-service.exe"]


buildOptions = dict(include_files=files)

build_exe_options = {"packages": ["pyodbc","checks"],"include_files":files}

executables = [
    Executable('runner.py'),
    Executable('collector_mgr.py'),
    Executable('deploy/windows/windows_deploy.py'),
    Executable("deploy/windows/filebeat_conf.py")
]

setup(name='cloudwiz-agent',
      version='0.1',
      description='collectors',
      executables=executables,
      options=dict(build_exe=build_exe_options),
      )
