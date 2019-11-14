name "psutil"
default_version "5.6.3"

python_version = ENV['PYTHON_VERSION']

if python_version.nil? || python_version.empty? || python_version == "3"
  dependency "python3"
elsif python_version == "2"
  dependency "python"
  dependency 'pip'
end

source :url => "https://github.com/giampaolo/psutil/archive/release-#{version}.tar.gz"

version "5.6.3" do
  source :sha256 => "55b86dc0a9fc4e258ae5d86d6edf317432a4e3dc45c7324b8a82838b07e74f4a"
end

relative_path "psutil-release-#{version}"


build do
  ship_license "https://raw.githubusercontent.com/giampaolo/psutil/master/LICENSE"

  if aix?
    env = aix_env 
  else
    env = with_standard_compiler_flags(with_embedded_path)
  end

  if aix?
    patch source: "aix-net-kernel-mbuf-header-fix.patch", plevel: 1

    env["M4"] = "/opt/freeware/bin/m4"
  end

  pip "install --no-cache-dir .", :env => env
end
