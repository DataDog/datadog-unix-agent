# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https:#www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

require "./lib/ostools.rb"

name 'agent'
package_name 'datadog-unix-agent'

homepage 'http://www.datadoghq.com'

install_dir '/opt/datadog-agent'
maintainer 'Datadog Packages <package@datadoghq.com>'

build_version do
  source :git
  output_format :dd_agent_format
end

build_iteration 1

description 'Datadog Monitoring Agent for UNIX platforms
 The Datadog Monitoring Agent is a lightweight process that monitors system
 processes and services, and sends information back to your Datadog account.
 .
 This package installs and runs the advanced Agent daemon, which queues and
 forwards metrics from your applications as well as system services.
 .
 See http://www.datadoghq.com/ for more information
'

# ------------------------------------
# Generic package information
# ------------------------------------

# .rpm specific flags
package :rpm do
  vendor 'Datadog <package@datadoghq.com>'
  epoch 1
  dist_tag ''
  license 'Apache License Version 2.0'
  category 'System Environment/Daemons'
  priority 'extra'
  if ENV.has_key?('RPM_SIGNING_PASSPHRASE') and not ENV['RPM_SIGNING_PASSPHRASE'].empty?
    signing_passphrase "#{ENV['RPM_SIGNING_PASSPHRASE']}"
  end
end

# ------------------------------------
# Dependencies
# ------------------------------------

dependency 'cacerts'
dependency "libffi"

python_version = ENV['PYTHON_VERSION']

if python_version.nil? || python_version.empty? || python_version == "3"
  dependency "python3"
elsif python_version == "2"
  dependency "python"
  dependency 'pip'
end

## creates required build directories
dependency 'datadog-agent-prepare'

## agent dependencies
dependency 'datadog-agent-dependencies'

## Datadog agent
dependency 'datadog-agent'

## Additional software
dependency 'datadog-agent-integrations'
dependency 'jmxfetch'

# version manifest file
dependency 'version-manifest'

# this dependency puts few files out of the omnibus install dir and move them
# in the final destination. This way such files will be listed in the packages
# manifest and owned by the package manager. This is the only point in the build
# process where we operate outside the omnibus install dir, thus the need of
# the `extra_package_file` directive.
# This must be the last dependency in the project.


if aix?
  extra_package_file '/etc/datadog-agent/'
  extra_package_file '/var/log/datadog/'
  package_scripts_path "#{Omnibus::Config.project_root}/package-scripts/#{name}/aix"
end

exclude '\.git*'
exclude 'bundler\/git'
