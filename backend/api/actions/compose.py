from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sh import docker_compose
import os
import yaml
import pathlib
import shutil
import docker
import io
import zipfile

from api.settings import Settings
from api.utils.compose import find_yml_files

settings = Settings()

def compose_action(name, action):
    """
    Runs an action on the specified compose project.
    """
    files = find_yml_files(settings.COMPOSE_DIR)
    compose = get_compose(name)
    env = os.environ.copy()
    if action == "up":
        try:
            _action = docker_compose(
                action,
                "-d",
                _cwd=os.path.dirname(compose["path"]),
                _env=check_dockerhost(env),
            )
        except Exception as exc:
            if hasattr(exc, "stderr"):
                raise HTTPException(400, exc.stderr.decode("UTF-8").rstrip())
            else:
                raise HTTPException(400, exc)
    elif action == "create":
        try:
            _action = docker_compose(
                "up",
                "--no-start",
                _cwd=os.path.dirname(compose["path"]),
                _env=check_dockerhost(env),
            )
        except Exception as exc:
            if hasattr(exc, "stderr"):
                raise HTTPException(400, exc.stderr.decode("UTF-8").rstrip())
            else:
                raise HTTPException(400, exc)
    else:
        try:
            _action = docker_compose(
                action,
                _cwd=os.path.dirname(compose["path"]),
                _env=check_dockerhost(env),
            )
        except Exception as exc:
            if hasattr(exc, "stderr"):
                raise HTTPException(400, exc.stderr.decode("UTF-8").rstrip())
            else:
                raise HTTPException(400, exc)
    if _action.stdout.decode("UTF-8").rstrip():
        _output = _action.stdout.decode("UTF-8").rstrip()
    elif _action.stderr.decode("UTF-8").rstrip():
        _output = _action.stderr.decode("UTF-8").rstrip()
    else:
        _output = "No Output"
    print(f"""Project {compose['name']} {action} successful.""")
    print(f"""Output: """)
    print(_output)
    return get_compose_projects()

def check_dockerhost(environment):
    """
    Used to include the DOCKER_HOST in the shell env
    when someone ups a compose project or returns a
    useless var to just clear the shell env.
    """
    if environment.get("DOCKER_HOST"):
        return {"DOCKER_HOST": environment["DOCKER_HOST"]}
    else:
        return {"clear_env": "true"}


def compose_app_action(
    name,
    action,
    app,
):
    """
    Used to run docker-compose commands on specific 
    apps in compose projects.
    """
    files = find_yml_files(settings.COMPOSE_DIR)
    compose = get_compose(name)
    env = os.environ.copy()
    print("RUNNING: " + compose["path"] + " docker-compose " + " " + action + " " + app)
    if action == "up":
        try:
            _action = docker_compose(
                "up",
                "-d",
                app,
                _cwd=os.path.dirname(compose["path"]),
                _env=check_dockerhost(env),
            )
        except Exception as exc:
            if hasattr(exc, "stderr"):
                raise HTTPException(400, exc.stderr.decode("UTF-8").rstrip())
            else:
                raise HTTPException(400, exc)
    elif action == "create":
        try:
            _action = docker_compose(
                "up",
                "--no-start",
                app,
                _cwd=os.path.dirname(compose["path"]),
                _env=check_dockerhost(env),
            )
        except Exception as exc:
            if hasattr(exc, "stderr"):
                raise HTTPException(400, exc.stderr.decode("UTF-8").rstrip())
            else:
                raise HTTPException(400, exc)
    elif action == "build":
        try:
            _action = docker_compose(
                "build",
                "--pull",
                app,
                _cwd=os.path.dirname(compose["path"]),
                _env=check_dockerhost(env),
            )
        except Exception as exc:
            if hasattr(exc, "stderr"):
                raise HTTPException(400, exc.stderr.decode("UTF-8").rstrip())
            else:
                raise HTTPException(400, exc)
    elif action == "rm":
        try:
            _action = docker_compose(
                "rm",
                "--force",
                "--stop",
                app,
                _cwd=os.path.dirname(compose["path"]),
                _env=check_dockerhost(env),
            )
        except Exception as exc:
            if hasattr(exc, "stderr"):
                raise HTTPException(400, exc.stderr.decode("UTF-8").rstrip())
            else:
                raise HTTPException(400, exc)
    else:
        try:
            _action = docker_compose(
                action,
                app,
                _cwd=os.path.dirname(compose["path"]),
                _env=check_dockerhost(env),
            )
        except Exception as exc:
            if hasattr(exc, "stderr"):
                raise HTTPException(400, exc.stderr.decode("UTF-8").rstrip())
            else:
                raise HTTPException(400, exc)
    if _action.stdout.decode("UTF-8").rstrip():
        output = _action.stdout.decode("UTF-8").rstrip()
    elif _action.stderr.decode("UTF-8").rstrip():
        output = _action.stderr.decode("UTF-8").rstrip()
    else:
        output = "No Output"
    print(f"""Project {compose['name']} App {name} {action} successful.""")
    print(f"""Output: """)
    print(output)
    return get_compose_projects()

def get_compose_projects():
    """
    Checks for compose projects in the COMPOSE_DIR and
    returns most of the info inside them.
    """
    files = find_yml_files(settings.COMPOSE_DIR)

    projects = []
    for project, file in files.items():
        volumes = []
        networks = []
        services = {}
        compose = open(file)
        loaded_compose = yaml.load(compose, Loader=yaml.SafeLoader)
        if loaded_compose:
            if loaded_compose.get("volumes"):
                for volume in loaded_compose.get("volumes"):
                    volumes.append(volume)
            if loaded_compose.get("networks"):
                for network in loaded_compose.get("networks"):
                    networks.append(network)
            if loaded_compose.get("services"):
                for service in loaded_compose.get("services"):
                    services[service] = loaded_compose["services"][service]
            _project = {
                "name": project,
                "path": file,
                "version": loaded_compose.get("version", "3.9"),
                "services": services,
                "volumes": volumes,
                "networks": networks,
            }
            projects.append(_project)
        else:
            print("ERROR: " + file + " is invalid or empty!")
    return projects

def get_compose(name):
    """
    Returns detailed information on a specific compose
    project.
    """
    try:
        files = find_yml_files(settings.COMPOSE_DIR + name)
    except Exception as exc:
        raise HTTPException(exc.status_code, exc.detail)
    for project, file in files.items():
        if name == project:
            networks = []
            volumes = []
            services = {}
            compose = open(file)
            try:
                loaded_compose = yaml.load(compose, Loader=yaml.SafeLoader)
            except yaml.scanner.ScannerError as exc:
                raise HTTPException(422, f"{exc.problem_mark.line}:{exc.problem_mark.column} - {exc.problem}")
            if loaded_compose.get("volumes"):
                for volume in loaded_compose.get("volumes"):
                    volumes.append(volume)
            if loaded_compose.get("networks"):
                for network in loaded_compose.get("networks"):
                    networks.append(network)
            if loaded_compose.get("services"):
                for service in loaded_compose.get("services"):
                    services[service] = loaded_compose["services"][service]
            _content = open(file)
            content = _content.read()
            compose_object = {
                "name": project,
                "path": file,
                "version": loaded_compose.get("version", "-"),
                "services": services,
                "volumes": volumes,
                "networks": networks,
                "content": content,
            }
            return compose_object
    else:
        raise HTTPException(404, "Project " + name + " not found")

def write_compose(compose):
    """
    Creates a compose directory (if one isn't there
    already) with the name of the project. Then writes
    the content of compose.content to it.
    """
    if not os.path.exists(settings.COMPOSE_DIR + compose.name):
        try:
            pathlib.Path(settings.COMPOSE_DIR + compose.name).mkdir(parents=True)
        except Exception as exc:
            raise HTTPException(exc.status_code, exc.detail)
    compose_name = find_yml_files(settings.COMPOSE_DIR + compose.name)[compose.name].split("/")[-1]
    with open(settings.COMPOSE_DIR + compose.name + "/" + compose_name, "w") as f:
        try:
            f.write(compose.content)
            f.close()
        except TypeError as exc:
            if exc.args[0] == "write() argument must be str, not None":
                raise HTTPException(
                    status_code=422, detail="Compose file cannot be empty."
                )
        except Exception as exc:
            raise HTTPException(exc.status_code, exc.detail)

    return get_compose(name=compose.name)

def delete_compose(project_name):
    """
    Deletes a compose project after checking to see if
    it exists. This also deletes all files in the folder.
    """
    try:
        compose_name = find_yml_files(settings.COMPOSE_DIR + project_name)[project_name].split("/")[-1]
    except:
        compose_name = "docker-compose.yml"

    if not os.path.exists("/" + settings.COMPOSE_DIR + project_name):
        raise HTTPException(404, "Project directory not found.")
    elif not os.path.exists(
        "/" + settings.COMPOSE_DIR + project_name + "/" + compose_name
    ):
        raise HTTPException(404, "Project docker-compose.yml not found.")
    else:
        try:
            with open(
                "/" + settings.COMPOSE_DIR + project_name + "/" + compose_name
            ):
                pass
        except OSError as exc:
            raise HTTPException(400, exc.strerror)
    try:
        shutil.rmtree("/" + settings.COMPOSE_DIR + project_name)
    except Exception as exc:
        raise HTTPException(exc.status_code, exc.strerror)
    return get_compose_projects()

def is_safe_path(base_dir, target_file):
    """
    Checks if target_file is inside the base directory.
    This is to prevent path traversal attacks.
    """
    match_path = os.path.abspath(target_file)
    return (base_dir == os.path.commonpath((base_dir, match_path)), match_path)

def get_project_file(project_name, file_name, skip_check=False):
    """
    Reads the contents of specified file from the
    project directory.
    """
    safe_path, abs_path = is_safe_path(
        settings.COMPOSE_DIR + project_name, settings.COMPOSE_DIR + project_name + "/" + file_name
    )
    if skip_check or safe_path:
        content = ""
        with open(abs_path, 'r') as project_file:
            content = project_file.read()
        return {"name": file_name, "content": content, "project": project_name}
    else:
        raise HTTPException(403, f"{file_name} is not in project directory.")

def write_project_file(project_name, file_name, file_data):
    """
    Write the contents of specified file to the
    project directory.
    """
    safe_path, abs_path = is_safe_path(
        settings.COMPOSE_DIR + project_name, settings.COMPOSE_DIR + project_name + "/" + file_name
    )
    if safe_path:
        with open(abs_path, 'w') as project_file:
            project_file.write(file_data.content)
        return get_project_file(project_name, file_name, skip_check=True)
    else:
        raise HTTPException(403, f"{file_name} is not in project directory.")

def generate_support_bundle(project_name):
    files = find_yml_files(settings.COMPOSE_DIR + project_name)
    if project_name in files:
        dclient = docker.from_env()
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as zf, open(files[project_name], "r") as fp:
            compose = yaml.load(fp, Loader=yaml.SafeLoader)
            # print(compose)
            # print(compose.get("services"))
            for _service in compose.get("services"):
                print()
                if len(compose.get("services").keys()) < 2:
                    try:
                        if compose.get("services")[_service].get("container_name"):
                            service = dclient.containers.get(
                                compose.get("services")[_service].get("container_name")
                            )
                        else:
                            service = dclient.containers.get(_service)
                    except docker.errors.NotFound as exc:
                        raise HTTPException(
                            exc.status_code,
                            detail="container " + _service + " not found",
                        )
                else:
                    try:
                        if compose.get("services")[_service].get("container_name"):
                            service = dclient.containers.get(
                                compose.get("services")[_service].get("container_name")
                            )
                        else:
                            service = dclient.containers.get(
                                project_name.lower() + "_" + _service + "_1"
                            )
                    except docker.errors.NotFound as exc:
                        raise HTTPException(
                            exc.status_code,
                            detail="container " + _service + " not found",
                        )
                service_log = service.logs()
                zf.writestr(f"{_service}.log", service_log)
            fp.seek(0)
            # It is possible that ".write(...)" has better memory management here.
            zf.writestr("docker-compose.yml", fp.read())
        stream.seek(0)
        return StreamingResponse(
            stream,
            media_type="application/x-zip-compressed",
            headers={
                "Content-Disposition": f"attachment;filename={project_name}_bundle.zip"
            },
        )
    else:
        raise HTTPException(404, f"Project {project_name} not found.")
