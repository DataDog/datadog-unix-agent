#
# Copyright:: Copyright (c) 2013-2014 Chef Software, Inc.
# License:: Apache License, Version 2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

name "python"

default_version "2.7.15"

dependency "ncurses"
dependency "zlib"
dependency "openssl"
dependency "bzip2"
dependency "libsqlite3"

source :url => "http://python.org/ftp/python/#{version}/Python-#{version}.tgz",
       :sha256 => "18617d1f15a380a919d517630a9cd85ce17ea602f9bbdc58ddc672df4b0239db"

relative_path "Python-#{version}"

default_version "2.7.15"

build do
  ship_license "PSFL"
  patch :source => "python-2.7.11-avoid-allocating-thunks-in-ctypes.patch" if linux?
  patch :source => "python-2.7.11-fix-platform-ubuntu.diff" if linux?

  if aix?
    env = aix_env
  else
    env = with_standard_compiler_flags(with_embedded_path)
  end
  
  python_configure = ["./configure",
                      "--enable-universalsdk=/",
                      "--prefix=#{install_dir}/embedded"]
  
  if mac_os_x?
    python_configure.push("--enable-ipv6",
                          "--with-universal-archs=intel",
                          "--enable-shared")
  elsif linux? || aix?
    python_configure.push("--enable-unicode=ucs4")
  end
  
  python_configure.push("--with-dbmliborder=")


  command python_configure.join(" "), :env => env
  if aix?
    command "make", :env => env
  else
    command "make -j #{workers}", :env => env
  end
  command "make install", :env => env
  delete "#{install_dir}/embedded/lib/python2.7/test"

  # There exists no configure flag to tell Python to not compile readline support :(
  block do
    FileUtils.rm_f(Dir.glob("#{install_dir}/embedded/lib/python2.7/lib-dynload/readline.*"))
  end
end
