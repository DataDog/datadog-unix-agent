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

version "1.2.1" do
  source :sha256 => "00ac0c2bfaa087de634a73a4e348f535f69c386fabf762adb4841728b5fe88b1"
end

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
    env["CFLAGS"] = "-fPIC #{env["CFLAGS"]}"
    env["CXXFLAGS"] = "-fPIC #{env["CXXFLAGS"]}"
    # pynacl's setup.py runs `make check` on bundled libsodium 1.0.20.
    # pwhash_scrypt crashes on AIX; suppress test compilation and execution.
    env["LIBSODIUM_MAKE_ARGS"] = "check_PROGRAMS= TESTS="
  end

  pip "install wheel", :env => env
  pip "install --no-cache-dir .", :env => env
end
