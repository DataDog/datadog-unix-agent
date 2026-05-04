name "python3"

default_version "3.8.10"

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
  patch source: "no-libintl.patch", plevel:1

  command python_configure.join(" "), :env => env
  command "make", :env => env
  command "make install", :env => env
  delete "#{install_dir}/embedded/lib/python3.8/test"

  if aix?
    # AIX: ld_so_aix emits "Entry point not found" warnings that Python's setup.py
    # treats as build failures, leaving _ssl/_hashlib as _failed.so stubs even though
    # the .so files link and load correctly.  Re-run sharedmods with minimal env to
    # force a clean build, then manually install the resulting .so files.
    dynload = "#{install_dir}/embedded/lib/python3.8/lib-dynload"
    # allow non-zero exit (e.g. _tkinter fails due to missing 32-bit Tk lib — expected)
    command "make sharedmods || true", :env => {"OBJECT_MODE" => "64",
                                                "PATH" => env["PATH"],
                                                "LIBPATH" => "#{install_dir}/embedded/lib:/usr/lib:/lib"}
    command "cp build/lib.aix-7.2-3.8/_ssl.cpython-38.so #{dynload}/_ssl.cpython-38.so"
    command "cp build/lib.aix-7.2-3.8/_hashlib.cpython-38.so #{dynload}/_hashlib.cpython-38.so"
    command "rm -f #{dynload}/_ssl.cpython-38_failed.so #{dynload}/_hashlib.cpython-38_failed.so"
  end

  link "#{install_dir}/embedded/bin/python3", "#{install_dir}/embedded/bin/python"
  link "#{install_dir}/embedded/bin/pip3", "#{install_dir}/embedded/bin/pip"
  # Install pip 21.1.3 from local wheel (no network needed; avoids ssl bootstrap issue on AIX)
  # The wheel is pre-staged at /tmp/pip-21.1.3-py3-none-any.whl by the build bootstrap process
  pip "install --upgrade --no-index --find-links /tmp pip==21.1.3", env: env
end
