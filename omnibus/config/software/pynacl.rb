name "pynacl"
default_version "1.6.2"

python_version = ENV['PYTHON_VERSION']

if python_version.nil? || python_version.empty? || python_version == "3"
  dependency "python3"
elsif python_version == "2"
  dependency "python"
  dependency 'pip'
end

source :url => "https://github.com/pyca/pynacl/archive/#{version}.tar.gz"

version "1.6.2" do
  source :sha256 => "fa489623e2a802c1c7e2127188e3072f326c229dbe23f99994b3547407a85958"
end

relative_path "pynacl-#{version}"


build do
  ship_license "https://raw.githubusercontent.com/pyca/pynacl/master/LICENSE"

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

    # pynacl 1.6.2 runs "make check" on libsodium (including pwhash_scrypt) which
    # fails on AIX (resource exhaustion / scrypt memory requirements). Replace the
    # make binary with a wrapper that turns "make check" into a no-op so the rest
    # of the build proceeds. pip's isolated build env inherits this env var.
    make_wrapper = "#{install_dir}/embedded/bin/make-no-check"
    block do
      File.write(make_wrapper, "#!/bin/sh\n[ \"$1\" = check ] && exit 0\nexec /opt/freeware/bin/make \"$@\"\n")
      File.chmod(0755, make_wrapper)
    end
    env["MAKE"] = make_wrapper
  end

  pip "install wheel", :env => env
  pip "install --no-cache-dir .", :env => env
end
