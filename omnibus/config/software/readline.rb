name "readline"
default_version "7.0"

version "7.0" do
  source :sha256 => "750d437185286f40a369e1e4f4764eda932b9459b5ec9a731628393dd3d32334"
end

source :url => "https://ftp.gnu.org/gnu/readline/readline-#{version}.tar.gz"

relative_path "readline-#{version}"

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

  configure_command = ["./configure",
                       "--prefix=#{install_dir}/embedded"]

  if ohai["platform"] == "freebsd"
    configure_command << "--with-pic"
  end

  command configure_command.join(" "), :env => env

  # note: this patch is dependent on the environment we ./configure with
  # if that changes this patch will likely have to be generated again.
  patch :source => "readline-shlib-makefile-fix.patch", :plevel => 0 if ohai["platform_family"] == "aix"

  command "make", :env => env
  command "make install", :env => env
end
