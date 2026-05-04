name "libsqlite3"
default_version "3.7.7.1"

dependency "readline"

source :url => "https://github.com/LuaDist/libsqlite3/archive/refs/tags/3.7.7.1.tar.gz",
       :sha256 => "b1eb700a46a7429a1a587fadd31e8ef5a3fd84bb6a75b898715baf71fedc412e"

relative_path "libsqlite3-3.7.7.1"

env = {
}

build do

  env = case ohai["platform"]
        when "aix"
          aix_env
        else
          {
            "LDFLAGS" => "-L#{install_dir}/embedded/lib -I#{install_dir}/embedded/include",
            "CFLAGS" => "-L#{install_dir}/embedded/lib -I#{install_dir}/embedded/include",
            "LD_RUN_PATH" => "#{install_dir}/embedded/lib",
          }
        end

  command(["./configure",
       "--prefix=#{install_dir}/embedded",
       "--disable-nls"].join(" "),
    :env => env)
  command "make", :env => env 
  command "make install"
  delete "#{install_dir}/embedded/bin/sqlite3"
end
