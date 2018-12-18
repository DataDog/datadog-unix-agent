# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https:#www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

require './lib/ostools.rb'

name 'datadog-agent-integrations'

python_version = ENV['PYTHON_VERSION']

if python_version.nil? || python_version.empty? || python_version == "3"
  dependency "python3"
elsif python_version == "2"
  dependency "python"
  dependency 'pip'
end

# some deps we need to build manually with omnibus
dependency 'datadog-agent-dependencies'

source path: '..'

requirements_file = 'requirements.txt'

blacklist = [
  'datadog_checks_base',           # namespacing package for wheels (NOT AN INTEGRATION)
]

build do

  checks = []

  if aix?
    env = aix_env 
    env["M4"] = "/opt/freeware/bin/m4"
  else
    env = with_standard_compiler_flags(with_embedded_path)
  end

  block 'pip install integrations wheels' do
    # install base wheel first
    pip "install -r #{project_dir}/#{requirements_file} .",
        :env => env,
        :cwd => "#{project_dir}/checks/bundled/datadog_checks_base"

    # install integrations
    Dir.glob("#{project_dir}/checks/bundled/*").each do |check_dir|

      check = check_dir.split('/').last

      next if !File.directory?("#{check_dir}") || blacklist.include?(check)

      pip "install -r #{project_dir}/#{requirements_file} .",
          :env => env,
          :cwd => "#{check_dir}"

    end
  end
end
