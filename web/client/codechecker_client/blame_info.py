import json
import os
import zipfile

from git import Repo
from git.exc import InvalidGitRepositoryError, GitCommandError
from typing import Dict, Iterable, Optional

from codechecker_common.compatibility.multiprocessing import Pool
from codechecker_common.logger import get_logger

LOG = get_logger('system')


FileBlameInfo = Dict[str, Optional[Dict]]


def __get_tracking_branch(repo: Repo) -> Optional[str]:
    """
    Get the tracking branch name or the current commit hash from the given
    repository.
    """
    try:
        # If a commit is checked out, accessing the active_branch member will
        # throw an error.
        return str(repo.active_branch.tracking_branch())
    except Exception:
        pass

    try:
        # Use the current commit hash if it's available.
        return repo.head.commit.hexsha
    except Exception:
        pass

    return None


def __get_blame_info(file_path: str):
    """ Get blame info for the given file. """
    try:
        real_path = os.path.realpath(file_path)
        repo = Repo(real_path, search_parent_directories=True)
        if repo.ignored(real_path):
            LOG.debug("File %s is an ignored file", file_path)
            return None
    except InvalidGitRepositoryError:
        return None
    except GitCommandError as ex:
        LOG.debug("Failed to get blame information for %s: %s", file_path, ex)
        return None

    tracking_branch = __get_tracking_branch(repo)

    remote_url = None
    try:
        # Handle the use case when a repository doesn't have a remote url.
        remote_url = next(repo.remote().urls, None)
    except Exception:
        pass

    try:
        blame = repo.blame_incremental(repo.head.commit.hexsha, real_path)

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

    return None


def __collect_blame_info_for_files(
    file_paths: Iterable[str],
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
    file_paths: Iterable[str]
) -> int:
    """
    Collect and write blame information for the given files to the zip file.

    Returns the number of collected blame information.
    """
    with Pool() as executor:
        file_blame_info = __collect_blame_info_for_files(
            file_paths, executor.map)

    # Add blame information to the zip for the files which will be sent
    # to the server if exist.
    for f, blame_info in file_blame_info.items():
        if blame_info:
            zip_file.writestr(
                os.path.join('blame', f.lstrip('/')),
                json.dumps(blame_info))

    return sum(bool(v) for v in file_blame_info.values())
