#!/bin/bash -eu
# Lionstone's core is standard-library only, so nothing else is installed.
pip3 install --no-deps .
for fuzzer in $(find "$SRC/lionstone/fuzz" -name '*_fuzzer.py'); do
  compile_python_fuzzer "$fuzzer"
done
