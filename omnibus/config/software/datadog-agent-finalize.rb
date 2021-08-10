# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https:#www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# This software definition doesn"t build anything, it"s the place where we create
# files outside the omnibus installation directory, so that we can add them to
# the package manifest using `extra_package_file` in the project definition.
require './lib/ostools.rb'

name "datadog-agent-finalize"
description "steps required to finalize the build"
default_version "1.0.0"
skip_transitive_dependency_licensing true

python_version = ENV['PYTHON_VERSION']
if python_version.nil? || python_version.empty? || python_version == "3"
  dependency "python3"
elsif python_version == "2"
  dependency "python"
  dependency 'pip'
end

build do
  python_path = "#{install_dir}/embedded/bin/python"
  pyc_compiled_files = "#{install_dir}/embedded/.pyc_compiled_files.txt"
  pyc_mask_re = "lib\/python.*\/test/.*|lib\/python.*\/lib2to3\/tests/.*"

  block do
    etc_dir = "/etc/datadog-agent"
    var_dir = "/var/log/datadog"

    # compile pyc files
    command "#{python_path} -m compileall #{install_dir} -x '#{pyc_mask_re}'"
    command "find . -type f -name '*.pyc' >> #{pyc_compiled_files}", :cwd => install_dir

    # Conf files
    if aix?
      whitelist = [
        "#{install_dir}/embedded/lib/libreadline.so",
        "#{install_dir}/embedded/lib/libreadline.so.7",
        "#{install_dir}/embedded/lib/libtinfo.so",
        "#{install_dir}/embedded/lib/libtinfo.so.5",
        "#{install_dir}/embedded/lib/libtinfo.so.5.9.0",
        "#{install_dir}/embedded/lib/libtinfow.so",
        "#{install_dir}/embedded/lib/libtinfow.so.5",
        "#{install_dir}/embedded/lib/libtinfow.so.5.9.0",
        "#{install_dir}/embedded/lib/python3.8/lib-dynload/fcntl.cpython-38.so",
        "#{install_dir}/embedded/lib/python3.8/lib-dynload/nis.cpython-38.so",
        "#{install_dir}/embedded/lib/python3.8/lib-dynload/readline.cpython-38.so",
        "#{install_dir}/embedded/lib/python3.8/site-packages/psutil/_psutil_aix.cpython-38.so",
        "#{install_dir}/embedded/bin/python",
        "#{install_dir}/embedded/bin/python3",
        "#{install_dir}/embedded/bin/python3.8",
      ]

      # Move checks and configuration files
      mkdir "#{etc_dir}"
      move "#{install_dir}#{etc_dir}/datadog.yaml.example", "#{etc_dir}"
      move "#{install_dir}#{etc_dir}/conf.d", "#{etc_dir}", :force=>true

      # Create empty directories so that they're owned by the package
      # (also requires `extra_package_file` directive in project def)
      mkdir "#{etc_dir}/checks.d"
      mkdir "#{var_dir}"

      project.extra_package_file("#{etc_dir}")
      project.extra_package_file("#{var_dir}")

      # cleanup clutter
      delete "#{install_dir}/etc"

      # FIXME: temporarily whitelist libs until we figure out the deps that are actually safe and those we need to fix
      whitelist.each { |elem|
        whitelist_file elem
      }
    end
  end
end

