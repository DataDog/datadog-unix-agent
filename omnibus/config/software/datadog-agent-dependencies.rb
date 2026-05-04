# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https:#www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

require './lib/ostools.rb'
require 'json'

name 'datadog-agent-dependencies'

python_version = ENV['PYTHON_VERSION']

if python_version.nil? || python_version.empty? || python_version == "3"
  dependency "python3"
elsif python_version == "2"
  dependency "python"
  dependency 'pip'
end

# some deps we need to build manually with omnibus
dependency 'libffi'  # required by cffi
dependency 'pynacl'

# relative_path 'integrations-core'
# whitelist_file "embedded/lib/python2.7"

# lxml native dependencies
dependency "libxml2"
dependency "libxslt"

dependency 'psutil'

source path: '..'

requirements_file = 'requirements.txt'

build do
  # The dir for the confs
  if osx?
    conf_dir = "#{install_dir}/etc/conf.d"
  else
    conf_dir = "#{install_dir}/etc/datadog-agent/conf.d"
  end
  mkdir conf_dir

  if aix?
    env = aix_env 
  else
    env = with_standard_compiler_flags(with_embedded_path)
  end

  if aix?
    env["M4"] = "/opt/freeware/bin/m4"

    # Let's set the PIC flag and see how it goes.
    env["CFLAGS"] = "-fPIC #{env["CFLAGS"]} -D__64BIT__"
    env["CXXFLAGS"] = "-fPIC #{env["CXXFLAGS"]} -D__64BIT__"

    # lxml's setup.py checks these env vars before falling back to PATH search.
    # lxml 4.9+ uses WITH_XML2_CONFIG/WITH_XSLT_CONFIG (XML2_CONFIG/XSLT_CONFIG are deprecated).
    env["WITH_XML2_CONFIG"] = "#{install_dir}/embedded/bin/xml2-config"
    env["WITH_XSLT_CONFIG"] = "#{install_dir}/embedded/bin/xslt-config"
  end

  if aix?
    # lxml's setup.py uses xml2-config/xslt-config for library detection.
    # --no-build-isolation bypasses pip's isolated build env so PATH and
    # WITH_XML2_CONFIG/WITH_XSLT_CONFIG are visible during setup.py egg_info.
    # Must run before requirements.txt so pip skips lxml when processing it.
    pip "install --no-cache-dir --no-build-isolation lxml==4.9.4", :env => env
  end

  # --no-build-isolation avoids pip's isolated build envs which break multiple packages on AIX:
  # - lxml egg_info can't find xslt-config via PATH in isolated env (handled above separately)
  # - PyYAML 5.4.1 hits AttributeError: cython_sources with newer setuptools in isolated env
  # - other C-extension packages may hit similar PEP 517 isolation issues
  pip_flags = aix? ? "--no-cache-dir --no-build-isolation" : "--no-cache-dir"
  pip "install #{pip_flags} -r #{project_dir}/#{requirements_file}", :env => env

end
