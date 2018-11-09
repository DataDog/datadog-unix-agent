# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https:#www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

require './lib/ostools.rb'
require 'pathname'

name 'datadog-agent'

dependency 'python'

license "Apache-2.0"
license_file "../LICENSE"

source path: '..'
relative_path 'src/github.com/DataDog/datadog-unix-agent'

build do
  # set GOPATH on the omnibus source dir for this software
  gopath = Pathname.new(project_dir) + '../../../..'
  etc_dir = "/etc/datadog-agent"
  env = {
    'GOPATH' => gopath.to_path,
    'PATH' => "#{gopath.to_path}/bin:#{ENV['PATH']}",
  }
  # include embedded path (mostly for `pkg-config` binary)
  env = with_embedded_path(env)

  # we assume the go deps are already installed before running omnibus
  command "invoke agent.build --rebuild --use-embedded-libs --no-development", env: env

  conf_dir = "#{install_dir}/etc/datadog-agent"

  mkdir conf_dir
  mkdir "#{install_dir}/run/"
  mkdir "#{install_dir}/scripts/"

  ## move around bin and config files
  # move 'bin/agent/dist/datadog.yaml', "#{conf_dir}/datadog.yaml.example"
  # move 'bin/agent/dist/network-tracer.yaml', "#{conf_dir}/network-tracer.yaml.example"
  # move 'bin/agent/dist/conf.d', "#{conf_dir}/"

  copy 'bin', install_dir

  if linux?
    if debian?
      erb source: "upstart_debian.conf.erb",
          dest: "#{install_dir}/scripts/datadog-agent.conf",
          mode: 0644,
          vars: { install_dir: install_dir, etc_dir: etc_dir }
      erb source: "sysvinit_debian.erb",
          dest: "#{install_dir}/scripts/datadog-agent",
          mode: 0755,
          vars: { install_dir: install_dir, etc_dir: etc_dir }
    end
  end
end
