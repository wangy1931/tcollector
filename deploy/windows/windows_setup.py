from cx_Freeze import setup, Executable


# collectors_files=["builtin","conf","etc","lib","__init__.py"]
files=["runner.conf",
       "collectors/",
       "deploy/windows/altenv",
       "lib/cloudwiz-service.exe"]


buildOptions = dict(include_files=files)

build_exe_options = {"packages": ["pyodbc","urllib","urllib3","win32com","config","getpass","os","psutil","platform","wmi"],"include_files":files}

executables = [
    Executable('runner.py',targetName="runner.exe"),
    Executable('collector_mgr.py',targetName="collector_mgr.exe"),
    Executable('deploy/windows/windows_deploy.py',targetName="windows_deploy.exe"),
    Executable("deploy/windows/filebeat_conf_imp.py")
]

setup(name='cloudwiz-agent',
      version='0.1',
      description='collectors',
      executables=executables,
      options=dict(build_exe=build_exe_options),
      )
