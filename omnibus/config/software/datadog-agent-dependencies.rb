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
#dependency 'libffi'  # required by cffi
#dependency 'psutil'

# relative_path 'integrations-core'
# whitelist_file "embedded/lib/python2.7"

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
  end

  ## NOTE: we might have to wrap ALL this remaining code in a `block do...end`

  pip "install --no-cache-dir -r #{project_dir}/#{requirements_file}", :env => env

end
