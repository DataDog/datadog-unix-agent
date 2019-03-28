name "pynacl"
default_version "1.2.1"

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

relative_path "pynacl-#{version}"


build do
  ship_license "https://raw.githubusercontent.com/pyca/pynacl/master/LICENSE"

  if aix?
    env = aix_env
  else
    env = with_standard_compiler_flags(with_embedded_path)
  end

  if aix?
    patch source: "libsodium-disable-pwhash_scrypt-test.patch", plevel: 1

    env["M4"] = "/opt/freeware/bin/m4"

    # Let's set the PIC flag and see how it goes.
    env["CFLAGS"] = "-fPIC #{env["CFLAGS"]}"
    env["CXXFLAGS"] = "-fPIC #{env["CXXFLAGS"]}"
  end

  pip "install --no-cache-dir .", :env => env
end
