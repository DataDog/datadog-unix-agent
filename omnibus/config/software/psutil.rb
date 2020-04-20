name "psutil"
default_version "5.6.6"

python_version = ENV['PYTHON_VERSION']

if python_version.nil? || python_version.empty? || python_version == "3"
  dependency "python3"
elsif python_version == "2"
  dependency "python"
  dependency 'pip'
end

source :url => "https://github.com/giampaolo/psutil/archive/release-#{version}.tar.gz"

version "5.6.6" do
  source :sha256 => "8da6fe2743132ba65e86fa7fb7b3a73d5f24ed2e8d794f3fa66484ab6dba98a7"
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
