#!/usr/bin/env python3

import json
import logging
import pathlib
import re
from pathlib import Path
from zipfile import ZipFile

import matplotlib.pyplot as plt
import numpy as np
from scipy.sparse import save_npz
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.manifold import TSNE
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)


class FailZip:
    def __init__(self, file: pathlib.Path):
        self.file = file

    def __len__(self):
        with ZipFile(self.file) as outer_zipfile:
            return len(outer_zipfile.namelist())

    def __iter__(self):
        with ZipFile(self.file) as outer_zipfile:
            for outer_filename in outer_zipfile.namelist():
                parts = re.search(
                    (
                        r"archive/(?P<project_name>.*)/(?P<run_name>.*)/"
                        r"failed/(?P<file_name>[^_]*)_(?P<analyzer>[^_]*)_"
                    ),
                    outer_filename,
                )
                with ZipFile(outer_zipfile.open(outer_filename)) as inner_zipfile:
                    stderr = inner_zipfile.open("stderr").read().decode("utf-8")
                    yield {
                        "project_name": parts["project_name"],
                        "run_name": parts["run_name"],
                        "analyzer": parts["analyzer"],
                        "file_name": parts["file_name"],
                        "similarity_context": stderr,
                    }


def cleanup_crash_text(context: str):
    # Stackdump is the only relevant part,
    # if this is found, skip everything before it
    stackdump_filter = re.search(r"Stack dump:([\s\S]*)", context)
    if stackdump_filter:
        context = stackdump_filter.group(1)
    # Remove all pointer info
    de_pointered_context = re.sub(r"0x[0-9a-fA-F]+", "", context)
    return de_pointered_context


def ensure_json_file(filename, data, force=True, encoder="utf-8"):
    file = Path(filename)
    if force or not file.exists():
        file.write_text(json.dumps(data, indent=2), encoding=encoder)


class NumpyArrayEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        return json.JSONEncoder.default(self, o)


def calculate_similarity_matrix(contexts):
    ### Calculate similarity matrix
    # 1. TF-IDF
    # 2. Truncated SVD
    # 3. TSNE

    # Crete a sparse matrix of the TF-IDF embedding
    tsne_matrix = Path("tfidf_embedding.npz")
    tfidf = TfidfVectorizer()
    tfidf_embedding = tfidf.fit_transform(
        [cleanup_crash_text(c["similarity_context"]) for c in contexts]
    )

    # Reduce dimensionality of the TF-IDF embedding
    truncated_svd = TruncatedSVD(n_components=50)
    truncated_svd_embedding = truncated_svd.fit_transform(tfidf_embedding)

    # Create a TSNE embedding
    tsne = TSNE(init="random")
    tsne_embedding = tsne.fit_transform(truncated_svd_embedding)
    with open(tsne_matrix, "wb") as f:
        save_npz(f, tfidf_embedding)

    return tsne_embedding


def plot_results(tsne_embedding, contexts):
    projects = list(c["project_name"] for c in contexts)
    unique_projects = set(projects)
    colors = plt.cm.Set1(np.linspace(0, 1, len(unique_projects)))
    colormap = dict(zip(unique_projects, colors))

    _, ax = plt.subplots()

    legend_handles = {}

    # maintain a set of seen points, and if the new point is close, then do not annotate it
    # this is to avoid cluttering the plot
    # FIXME: We should do a real clustering instead of this hack
    seen_points = []

    for i, c in enumerate(contexts):
        project = c["project_name"]
        color = colormap[project]
        # Plot and caputure the scatter plot handle
        scatter = ax.scatter(
            tsne_embedding[i, 0],
            tsne_embedding[i, 1],
            c=[color],
            s=50,
            edgecolor="k",
            label=project,
            alpha=0.8,
        )

        legend_handles[project] = scatter

        # find the closest point in seen_points to this point
        closest_distance = min(np.linalg.norm(
            tsne_embedding[i] - seen_point) for seen_point in seen_points)

        # FIXME: arbitrary distance here...
        if closest_distance < 0.5:
            continue

        seen_points.append(tsne_embedding[i])

        ax.annotate(
            c["file_name"],
            tsne_embedding[i],
            textcoords="offset points",
            xytext=(0, 5),
            ha="center",
        )

    ax.legend(
        handles=list(legend_handles.values()),
        labels=list(legend_handles.keys()),
        title="Project Names",
        loc="lower left",
    )

    ax.set_title("Files")

    plt.savefig("tsne.png")
    plt.show()


def main():
    contexts = list(
        tqdm(FailZip(pathlib.Path("archive.zip")), desc="Reading failzips...")
    )
    tsne_embedding = calculate_similarity_matrix(contexts)
    plot_results(tsne_embedding, contexts)


if __name__ == "__main__":
    main()
