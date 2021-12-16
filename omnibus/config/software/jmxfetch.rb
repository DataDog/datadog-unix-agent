# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https:#www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

name "jmxfetch"

jmxfetch_version = ENV['JMXFETCH_VERSION']
jmxfetch_hash = ENV['JMXFETCH_HASH']

if jmxfetch_version.nil? || jmxfetch_version.empty?
  jmxfetch_version = '0.44.5'
  jmxfetch_hash = "938761d7d334c7bd38071445058df7309be3f93150d32dc1192120d679f5b466"
end

default_version jmxfetch_version
source sha256: jmxfetch_hash

source url: "https://oss.sonatype.org/service/local/repositories/releases/content/com/datadoghq/jmxfetch/#{version}/jmxfetch-#{version}-jar-with-dependencies.jar",
       target_filename: "jmxfetch.jar"

jar_dir = "#{install_dir}/bin/agent/dist/jmx"

relative_path "jmxfetch"

build do
  ship_license "https://raw.githubusercontent.com/DataDog/jmxfetch/master/LICENSE"
  mkdir jar_dir
  copy "jmxfetch.jar", "#{jar_dir}/jmxfetch.jar"
  block { File.chmod(0644, "#{jar_dir}/jmxfetch.jar") }
end
