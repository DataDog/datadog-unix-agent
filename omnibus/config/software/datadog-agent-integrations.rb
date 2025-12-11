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
  'hmc',                           # HMC in-development
]

build do

  checks = []

  if aix?
    env = aix_env
    env["M4"] = "/opt/freeware/bin/m4"
  else
    env = with_standard_compiler_flags(with_embedded_path)
  end

  conf_dir = "#{install_dir}/etc/datadog-agent/conf.d"
  mkdir conf_dir

  block 'pip install integrations wheels' do
    # install base wheel first
    pip "install -r #{project_dir}/#{requirements_file} .",
        :env => env,
        :cwd => "#{project_dir}/checks/bundled/datadog_checks_base"

    # install integrations
    Dir.glob("#{project_dir}/checks/bundled/*").each do |check_dir|

      check = check_dir.split('/').last

      next if !File.directory?("#{check_dir}") || blacklist.include?(check)

      check_conf_dir = "#{conf_dir}/#{check}.d"

      # For each conf file, if it already exists, that means the `datadog-agent` software def
      # wrote it first. In that case, since the agent's confs take precedence, skip the conf

      # Copy the check config to the conf directories
      conf_file_example = "#{check_dir}/datadog_checks/#{check}/data/conf.yaml.example"
      if File.exist? conf_file_example
        mkdir check_conf_dir
        copy conf_file_example, "#{check_conf_dir}/" unless File.exist? "#{check_conf_dir}/conf.yaml.example"
      end

      # Copy the default config, if it exists
      conf_file_default = "#{check_dir}/datadog_checks/#{check}/data/conf.yaml.default"
      if File.exist? conf_file_default
        mkdir check_conf_dir
        copy conf_file_default, "#{check_conf_dir}/" unless File.exist? "#{check_conf_dir}/conf.yaml.default"
      end

      # Copy the metric file, if it exists
      metrics_yaml = "#{check_dir}/datadog_checks/#{check}/data/metrics.yaml"
      if File.exist? metrics_yaml
        mkdir check_conf_dir
        copy metrics_yaml, "#{check_conf_dir}/" unless File.exist? "#{check_conf_dir}/metrics.yaml"
      end

      pip "install -r #{project_dir}/#{requirements_file} .",
          :env => env,
          :cwd => "#{check_dir}"

    end
  end

  block 'copy corecheck configs' do
    # Process corechecks from checks/corechecks/<category>/<checkname>/
    corecheck_categories = Dir.glob("#{project_dir}/checks/corechecks/*").select { |d| File.directory?(d) }
    
    corecheck_categories.each do |category_dir|
      category = category_dir.split('/').last
      
      # Skip __pycache__ and other non-category directories
      next if category.start_with?('__')
      
      # Process each check in the category
      Dir.glob("#{category_dir}/*").each do |check_dir|
        next unless File.directory?(check_dir)
        
        check = check_dir.split('/').last
        
        # Skip __pycache__ and test directories
        next if check.start_with?('__') || check == 'tests'
        
        check_conf_dir = "#{conf_dir}/#{check}.d"
        
        # Copy the default config, if it exists
        conf_file_default = "#{check_dir}/data/conf.yaml.default"
        if File.exist? conf_file_default
          mkdir check_conf_dir
          copy conf_file_default, "#{check_conf_dir}/" unless File.exist? "#{check_conf_dir}/conf.yaml.default"
        end
        
        # Copy the example config, if it exists
        conf_file_example = "#{check_dir}/data/conf.yaml.example"
        if File.exist? conf_file_example
          mkdir check_conf_dir
          copy conf_file_example, "#{check_conf_dir}/" unless File.exist? "#{check_conf_dir}/conf.yaml.example"
        end
      end
    end
  end
end
