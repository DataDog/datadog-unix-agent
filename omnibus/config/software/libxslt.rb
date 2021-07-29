

name "libxslt"
default_version "1.1.28"

dependency "libxml2"
dependency "libtool" if ohai["platform"] == "solaris2"
dependency "liblzma"
dependency "config_guess"

version "1.1.26" do
  source md5: "e61d0364a30146aaa3001296f853b2b9"
end

version "1.1.28" do
  source md5: "9667bf6f9310b957254fdcf6596600b7"
end

source url: "ftp://xmlsoft.org/libxml2/libxslt-#{version}.tar.gz"

relative_path "libxslt-#{version}"

build do
  env = aix_env

  update_config_guess

  command(["./configure",
           "--prefix=#{install_dir}/embedded",
           "--with-libxml-prefix=#{install_dir}/embedded",
           "--with-libxml-include-prefix=#{install_dir}/embedded/include",
           "--with-libxml-libs-prefix=#{install_dir}/embedded/lib",
           "--without-python",
           "--without-crypto"].join(" "),
    env: env)
  command "make", env: env
  command "make install", env: env
end
