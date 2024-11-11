#!/bin/bash

new_api_version=$1

if [[ -z "$new_api_version" ]]
then
  echo "Please specify the new API version for this script."
  echo -e "  Usage: ./change-api-version x.y.z\n"
  echo "Use x.y.z-dev<n> in case of developer packages."
  exit 1
fi

# Change API version in js files.
find -name package.json -exec sed -r -i s/\"version\":\ \"[^\"]+\"/\"version\":\ \"${new_api_version}\"/g {} \;

# Change API version in py files.
find -name setup.py -exec sed -r -i s/api_version\ =\ \'[^\']+\'/api_version\ =\ \'${new_api_version}\'/g {} \;

# Change API version in GUI dependencies.
sed -r -i "s#\"codechecker-api\":\ \"[^\"]+\"#\"codechecker-api\":\ \"file:../../api/js/codechecker-api-node/dist/codechecker-api-${new_api_version}.tgz\"#g" ../server/vue-cli/package.json
