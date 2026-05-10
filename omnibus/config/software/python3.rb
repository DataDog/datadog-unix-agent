name "python3"

default_version "3.10.20"

dependency "libffi"
dependency "ncurses"
dependency "zlib"
dependency "openssl"
dependency "bzip2"
dependency "libsqlite3"
dependency "xz"
dependency "gdbm"

version "3.6.7" do
  source :sha256 => "b7c36f7ed8f7143b2c46153b7332db2227669f583ea0cce753facf549d1a4239"
end

version "3.7.1" do
  source :sha256 => "36c1b81ac29d0f8341f727ef40864d99d8206897be96be73dc34d4739c9c9f06"
end

version "3.8.10" do
  source :sha256 => "b37ac74d2cbad2590e7cd0dd2b3826c29afe89a734090a87bf8c03c45066cb65"
end

version "3.10.20" do
  source :sha256 => "4ff5fd4c5bab803b935019f3e31d7219cebd6f870d00389cea53b88bbe935d1a"
end

source :url => "https://python.org/ftp/python/#{version}/Python-#{version}.tgz"

relative_path "Python-#{version}"

python_configure = ["./configure",
                    "--prefix=#{install_dir}/embedded"]

if mac_os_x?
  python_configure.push("--enable-ipv6",
                        "--with-universal-archs=intel",
                        "--enable-shared")
elsif linux?
  python_configure.push("--enable-unicode=ucs4")
elsif aix?
  python_configure.push("--with-openssl=#{install_dir}/embedded")
end

python_configure.push("--with-dbmliborder=")
python_configure.push("--disable-ipv6")

build do
  ship_license "PSFL"

  env = case ohai["platform"]
        when "aix"
          aix_env
        else
          {
            "CFLAGS" => "-I#{install_dir}/embedded/include -O2 -g -pipe",
            "LDFLAGS" => "-Wl,-rpath,#{install_dir}/embedded/lib -L#{install_dir}/embedded/lib",
          }
        end
  if aix?
    # AIX native /usr/bin/patch rejects unified diffs; call GNU patch explicitly
    patch_file = File.join(Omnibus::Config.project_root, "config", "patches", "python3", "no-libintl.patch")
    command "/opt/freeware/bin/patch -p1 -i #{patch_file}", env: env
  else
    patch source: "no-libintl.patch", plevel:1
  end

  workers = `nproc 2>/dev/null || sysctl -n hw.logicalcpu 2>/dev/null || echo 1`.strip.to_i
  workers = [workers, 1].max

  command python_configure.join(" "), :env => env
  command "make -j#{workers}", :env => env
  command "make install", :env => env
  delete "#{install_dir}/embedded/lib/python3.10/test"

  if aix?
    # AIX: ld_so_aix emits "Entry point not found" warnings that Python's setup.py
    # treats as build failures, leaving _ssl/_hashlib as _failed.so stubs even though
    # the .so files link and load correctly.  Re-run sharedmods with minimal env to
    # force a clean build, then manually install the resulting .so files.
    dynload = "#{install_dir}/embedded/lib/python3.10/lib-dynload"
    # allow non-zero exit (e.g. _tkinter fails due to missing 32-bit Tk lib — expected)
    command "make sharedmods || true", :env => {"OBJECT_MODE" => "64",
                                                "PATH" => env["PATH"],
                                                "LIBPATH" => "#{install_dir}/embedded/lib:/usr/lib:/lib"}
    command "sh -c 'cp build/lib.aix*-3.10/_ssl.cpython-310.so #{dynload}/_ssl.cpython-310.so'"
    command "sh -c 'cp build/lib.aix*-3.10/_hashlib.cpython-310.so #{dynload}/_hashlib.cpython-310.so'"
    command "rm -f #{dynload}/_ssl.cpython-310_failed.so #{dynload}/_hashlib.cpython-310_failed.so"
  end
  link "#{install_dir}/embedded/bin/python3", "#{install_dir}/embedded/bin/python"
  link "#{install_dir}/embedded/bin/pip3", "#{install_dir}/embedded/bin/pip"
  pip "install --upgrade pip==21.1.3", env: env # Update pip since the version 21.1.1 shipped with python 3.8.10 crashes
end
