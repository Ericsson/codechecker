import json
import os
import sys
import zipfile

from concurrent.futures import ProcessPoolExecutor
from git import Repo
from git.exc import InvalidGitRepositoryError
from typing import Dict, List, Optional

from codechecker_common.logger import get_logger

LOG = get_logger('system')


FileBlameInfo = Dict[str, Optional[Dict]]


def __get_blame_info(file_path: str):
    """ Get blame info for the given file. """
    try:
        repo = Repo(file_path, search_parent_directories=True)
    except InvalidGitRepositoryError:
        return

    tracking_branch = None
    try:
        # If a commit is checked out, accessing the active_branch member will
        # throw a type error. In this case we will use the current commit hash.
        tracking_branch = str(repo.active_branch.tracking_branch())
    except TypeError:
        tracking_branch = repo.head.commit.hexsha

    remote_url = None
    try:
        # Handle the use case when a repository doesn't have a remote url.
        remote_url = next(repo.remote().urls, None)
    except ValueError:
        pass

    try:
        blame = repo.blame_incremental(repo.head.commit.hexsha, file_path)

        res = {
            'version': 'v1',
            'tracking_branch': tracking_branch,
            'remote_url': remote_url,
            'commits': {},
            'blame': []}

        for b in blame:
            commit = b.commit

            if commit.hexsha not in res['commits']:
                res['commits'][commit.hexsha] = {
                    'author': {
                        'name': commit.author.name,
                        'email': commit.author.email,
                    },
                    'summary': commit.summary,
                    'message': commit.message,
                    'committed_datetime': str(commit.committed_datetime)}

            res['blame'].append({
                'from': b.linenos[0],
                'to': b.linenos[-1],
                'commit': commit.hexsha})

        LOG.debug("Collected blame info for %s", file_path)

        return res
    except Exception as ex:
        LOG.debug("Failed to get blame information for %s: %s", file_path, ex)


def __collect_blame_info_for_files(
    file_paths: List[str],
    zip_iter=map
) -> FileBlameInfo:
    """ Collect blame information for the given file paths. """
    file_blame_info = {}
    for file_path, blame_info in zip(file_paths,
                                     zip_iter(__get_blame_info, file_paths)):
        file_blame_info[file_path] = blame_info

    return file_blame_info


def assemble_blame_info(
    zip_file: zipfile.ZipFile,
    file_paths: List[str]
) -> bool:
    """
    Collect and write blame information for the given files to the zip file.

    Returns true if at least one blame information is collected.
    """
    # Currently ProcessPoolExecutor fails completely in windows.
    # Reason is most likely combination of venv and fork() not
    # being present in windows, so stuff like setting up
    # PYTHONPATH in parent CodeChecker before store is executed
    # are lost.
    if sys.platform == "win32":
        file_blame_info = __collect_blame_info_for_files(file_paths)
    else:
        with ProcessPoolExecutor() as executor:
            file_blame_info = __collect_blame_info_for_files(
                file_paths, executor.map)

    # Add blame information to the zip for the files which will be sent
    # to the server if exist.
    for f, blame_info in file_blame_info.items():
        if blame_info:
            zip_file.writestr(
                os.path.join('blame', f.lstrip('/')),
                json.dumps(blame_info))

    return any(v for v in file_blame_info.values())
