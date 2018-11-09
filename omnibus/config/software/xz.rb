name "xz"
default_version "5.2.4"

version "5.2.4" do
  source sha256: "be84b8840cb1f156711bee957c613e3bd56b36bbfc43bc144d9913955a391a83"
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
