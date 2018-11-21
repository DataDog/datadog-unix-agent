name "psutil"
default_version "5.4.6"

python_version = ENV['PYTHON_VERSION']

if python_version.nil? || python_version.empty? || python_version == "3"
  dependency "python3"
elsif python_version == "2"
  dependency "python2"
  dependency 'pip'
end

source :url => "https://github.com/giampaolo/psutil/archive/release-#{version}.tar.gz"

version "5.4.6" do
  source :sha256 => "1fbe56d7937410837ff4f8a250a9d80fcb652982982a0a2a999f906bcea4bafc"
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
