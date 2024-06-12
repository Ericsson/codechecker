# Failzip Crash Clustering

## Overview

This script is designed for processing and analyzing text data contained within zip files, focusing on extracting, filtering, and analyzing specific parts of the content. It supports functions such as text vectorization, dimensionality reduction, similarity matrix calculation, and data visualization. Primarily, it could be used for analyzing stack dumps or other structured text data by applying text analytics and visualization techniques.

### Key Features

- **Zip File Handling**: Class `FailZip` provides functionalities to work with collections of zip files, including content extraction and length determination.
- **Text Filtering and Analysis**: Implements filtering criteria to extract and preprocess relevant parts of the text data.
- **Dimensionality Reduction and Vectorization**: Uses Truncated SVD and TF-IDF vectorization to process and analyze textual data.
- **Data Visualization**: Leverages matplotlib and TSNE for generating plots to visualize the results of the text data analysis.
- **JSON Handling**: Handles JSON data encoding through the `NumpyArrayEncoder` class and related functions for ensuring JSON file structures and custom encoding of numpy arrays.

## Requirements

- Python 3.x
- Libraries: json, logging, pathlib, re, zipfile, matplotlib, numpy, scipy, sklearn, tqdm

Ensure all dependencies are installed using pip:

```bash
pip install matplotlib numpy scipy scikit-learn tqdm
```

### Usage
Copy a fail-zip to the current working directory of the script, ensure that the name is 'archive.zip', and run the script `cluster_crashes.py`.
The cluster plot is then opened interactively if possible, but an image with name 'tsne.png' is also generated in the current working directory.

