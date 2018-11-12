name "xz"
default_version "5.2.4"

version "5.2.4" do
  source sha256: "b512f3b726d3b37b6dc4c8570e137b9311e7552e8ccbab4d39d47ce5f4177145"
end

source url: "https://tukaani.org/xz/xz-#{version}.tar.gz"

relative_path "xz-#{version}"

build do
  env = case ohai["platform"]
        when "aix"
          aix_env
        else
          with_standard_compiler_flags
        end

  configure env: env

  make "-j #{workers}", env: env
  make "-j #{workers} install", env: env
end
