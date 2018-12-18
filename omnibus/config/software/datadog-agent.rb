# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https:#www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

require './lib/ostools.rb'
require 'pathname'

name 'datadog-agent'
always_build true

source path: '..'

python_version = ENV['PYTHON_VERSION']

if python_version.nil? || python_version.empty? || python_version == "3"
  dependency "python3"
elsif python_version == "2"
  dependency "python"
  dependency 'pip'
end
dependency "datadog-agent-dependencies"

license "Apache-2.0"
license_file "./LICENSE"

build do
  block 'setup agent' do
    etc_dir = "/etc/datadog-agent"
  
    if aix?
      env = aix_env 
      env["M4"] = "/opt/freeware/bin/m4"
    else
      env = with_standard_compiler_flags(with_embedded_path)
    end
  
    mkdir  "#{install_dir}/agent/"
  
    # Agent code
    copy 'aggregator', "#{install_dir}/agent/"
    copy 'api', "#{install_dir}/agent/"
    copy 'collector', "#{install_dir}/agent/"
    copy 'config', "#{install_dir}/agent/"
    copy 'checks', "#{install_dir}/agent/"
    copy 'docs', "#{install_dir}/agent/"
    copy 'dogstatsd', "#{install_dir}/agent/"
    copy 'forwarder', "#{install_dir}/agent/"
    copy 'metadata', "#{install_dir}/agent/"
    copy 'serialize', "#{install_dir}/agent/"
    copy 'utils', "#{install_dir}/agent/"
  
    copy '*.py', "#{install_dir}/agent/"
    copy 'requirements.txt', "#{install_dir}/agent/"
  
    # removing some stuff we don't really need to ship like this
    delete "#{install_dir}/agent/checks/bundled/"
  
    # Collect all the test dirs
    tests = Dir.glob("#{install_dir}/agent/*/tests")
    tests.each do |test|
      delete "#{test}"
    end
  
    conf_dir = "#{install_dir}/etc/datadog-agent/"
  
    mkdir conf_dir
    mkdir "#{install_dir}/run/"
    mkdir "#{install_dir}/var/log/datadog/"
    mkdir "#{install_dir}/scripts/"
  
    ## move around config files
    copy 'datadog.yaml.sample', "#{conf_dir}"
  end
end
