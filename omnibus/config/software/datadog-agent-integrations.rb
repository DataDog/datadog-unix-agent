# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https:#www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

require './lib/ostools.rb'
require 'json'

name 'datadog-agent-integrations'

dependency 'python3'

# some deps we need to build manually with omnibus
dependency 'pynacl'

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
    env["CFLAGS"] = "-fPIC #{env["CFLAGS"]}"
    env["CXXFLAGS"] = "-fPIC #{env["CXXFLAGS"]}"
  end

  ## NOTE: we might have to wrap ALL this remaining code in a `block do...end`

  pip "install --no-cache-dir -r #{project_dir}/#{requirements_file}", :env => env

    # install integrations
  # Dir.glob("#{project_dir}/*").each do |check_dir|
  #   check = check_dir.split('/').last

  #   next if !File.directory?("#{check_dir}") || blacklist.include?(check)

  #   # If there is no manifest file, then we should assume the folder does not
  #   # contain a working check and move onto the next
  #   manifest_file_path = "#{check_dir}/manifest.json"

  #   # If there is no manifest file, then we should assume the folder does not
  #   # contain a working check and move onto the next
  #   File.exist?(manifest_file_path) || next

  #   manifest = JSON.parse(File.read(manifest_file_path))
  #   manifest['supported_os'].include?(os) || next

  #   check_conf_dir = "#{conf_dir}/#{check}.d"

  #   # For each conf file, if it already exists, that means the `datadog-agent` software def
  #   # wrote it first. In that case, since the agent's confs take precedence, skip the conf

  #   # Copy the check config to the conf directories
  #   conf_file_example = "#{check_dir}/datadog_checks/#{check}/data/conf.yaml.example"
  #   if File.exist? conf_file_example
  #     mkdir check_conf_dir
  #     copy conf_file_example, "#{check_conf_dir}/" unless File.exist? "#{check_conf_dir}/conf.yaml.example"
  #   end

  #   # Copy the default config, if it exists
  #   conf_file_default = "#{check_dir}/datadog_checks/#{check}/data/conf.yaml.default"
  #   if File.exist? conf_file_default
  #     mkdir check_conf_dir
  #     copy conf_file_default, "#{check_conf_dir}/" unless File.exist? "#{check_conf_dir}/conf.yaml.default"
  #   end

  #   # Copy the metric file, if it exists
  #   metrics_yaml = "#{check_dir}/datadog_checks/#{check}/data/metrics.yaml"
  #   if File.exist? metrics_yaml
  #     mkdir check_conf_dir
  #     copy metrics_yaml, "#{check_conf_dir}/" unless File.exist? "#{check_conf_dir}/metrics.yaml"
  #   end

  #   # We don't have auto_conf on windows yet
  #   if os != 'windows'
  #     auto_conf_yaml = "#{check_dir}/datadog_checks/#{check}/data/auto_conf.yaml"
  #     if File.exist? auto_conf_yaml
  #       mkdir check_conf_dir
  #       copy auto_conf_yaml, "#{check_conf_dir}/" unless File.exist? "#{check_conf_dir}/auto_conf.yaml"
  #     end
  #   end

  #   File.file?("#{check_dir}/setup.py") || next
  #   if windows?
  #     command("#{python_bin} -m #{python_pip_no_deps}\\#{check}")
  #   else
  #     pip "install --no-deps .", :env => nix_build_env, :cwd => "#{project_dir}/#{check}"
  #   end
  # end
end
