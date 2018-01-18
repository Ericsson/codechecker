# Shell script for identifying new bugs if results are stored & updated in the same run

The following is a concise Shell script that can be used in a Jenkins or any
other CI engine. This will exit with return status `1`, failing the job, if
new bugs would be introduced into the codebase by John Doe.

> This is the earlier example's modified version which uses local comparison
> and does *NOT* store John Doe's bugs into the central database.

~~~bash
#!/bin/bash

# -- Configuration variables --

CC_SERVER="http://localhost:8555/tmux"
MASTER_RUN_NAME="tmux_master"
SOURCE_DIR="${WORKSPACE}/tmux"
BUILD_COMMAND="make"

ANALYZER_OPTIONS=""

# -- Configuration that don't USUALLY need to be edited, but can be, if required --
OUTPUT_DIR="${WORKSPACE}/analysis"
HTML_DIR="${WORKSPACE}/html"

# -- Execute CodeChecker --

# 1. Build your project with CodeChecker
pushd ${SOURCE_DIR}
CodeChecker log --build "${BUILD_COMMAND}" \
                --output "${OUTPUT_DIR}/compile_commands.json" \
  || { echo "Build failed"; exit 1; }

# 2. Run analysis
CodeChecker analyze "${OUTPUT_DIR}/compile_commands.json" \
                    --output "${OUTPUT_DIR}/reports" "${ANALYZER_OPTIONS}" \
  || { echo "Failed to run analysis"; exit 1; }

## ---------

# 3. Use the command-line diff tool too see if there are new bugs.

# Check if yesterday's run exists.
MASTER_EXISTS=$(CodeChecker cmd runs --url "${CC_SERVER}" --output csv | grep "${MASTER_RUN_NAME}")
if [ -z "${PREVIOUS_EXISTS}" ]
then
  echo "Can't check if new bugs were introduced."
  echo "Master run \"${MASTER_RUN_NAME}\" does not exist."

  exit 0
fi

# Execute the diff command and handle its output.
DIFF_CMD=$(cat << END \
  CodeChecker cmd diff --url "${CC_SERVER}"
                       --basename "${MASTER_RUN_NAME}"
                       --newname  "$(readlink -f "${OUTPUT_DIR}")"
                       --new
  END
)

# Assume that there are new bugs introduced, unless proven otherwise.
echo -n "1" > "${WORKSPACE}/was_output.txt"

eval "${DIFF_CMD}" | while read -r line
  do
    # If CodeChecker says there aren't new bugs, don't introduce them.
    if [[ "$line" =~ "- No results" ]]
    then
      # This file is needed because the output of "CodeChecker cmd diff"
      # may contain lines that are only information for the user, so we can
      # not rely on the existence of 'bugs.txt' as only indicator of new bugs.
      echo -n "0" > "${WORKSPACE}/was_output.txt"
    fi

    echo "${line}"
    echo "${line}" >> "${WORKSPACE}/bugs.txt"
  done

if [ ! -z "${HTML_DIR}" ]
then
  DIFF_CMD="${DIFF_CMD} --output html --clean --export-dir ${HTML_DIR}"
  eval "${DIFF_CMD}"

  echo "Bug visualisation HTML files generated at \"${HTML_DIR}\"."
fi

WAS_OUTPUT=$(cat "${WORKSPACE}/was_output.txt")
if [ $WAS_OUTPUT -eq 1 ]
then
  echo "New bugs would be introduced -- rejecting pull request!"
  exit 1
else
  echo "No new bugs! Modification good to go. :)"
  exit 0
fi
~~~

Please configure your CI loop to, in case of a failed build, send the
`${WORKSPACE}/bugs.txt` files and the `${HTML_DIR}` folder to the project
maintainers and the commit's author (John Doe).

This can be done via e-mail sending, setting these as attachments, or copying
these files into a persistent (outside the CI job's workspace!) place and
sending its URL to the maintainers.

The return code of this script can be further used in the CI job to set ticket
or pull request status on the code tracker (such as Gerrit or GitLab).
