# ------------------------------------
# OS-detection helper functions
# ------------------------------------
def linux?()
    return %w(rhel debian fedora suse gentoo slackware arch exherbo).include? ohai['platform_family']
end

def redhat?()
    return %w(rhel fedora).include? ohai['platform_family']
end

def suse?()
    return %w(suse).include? ohai['platform_family']
end

def debian?()
    return ohai['platform_family'] == 'debian'
end

def osx?()
    return ohai['platform_family'] == 'mac_os_x'
end

def windows?()
    return ohai['platform_family'] == 'windows'
end

def aix?()
    return ohai['platform'] == 'aix'
end

def aix_env()
    env = with_standard_compiler_flags(with_embedded_path, :aix => { :use_gcc => true }) 
    env.merge({"LD_RUN_PATH" => "#{install_dir}/embedded/lib"})
    env["CC"] = "gcc -maix64"
    env["CXX"] = "gcc -maix64"
    env["ARFLAGS"] = "-X64 -cru"
    env["CFLAGS"] = "#{env["CFLAGS"].gsub('-q64', '')}"
    env["CPPFLAGS"] = "-P #{env["CPPFLAGS"].gsub('-q64', '')}"
    env["CXXFLAGS"] = "#{env["CXXFLAGS"].gsub('-q64', '')}"
    env["LDFLAGS"] = "#{env["LDFLAGS"].gsub('-q64', '')} -Wl,-brtl"
    env["NM"] = "/usr/bin/nm -X64"

    return env
end

def os
    case RUBY_PLATFORM
    when /linux/
      'linux'
    when /darwin/
      'mac_os'
    when /x64-mingw32/
      'windows'
    else
      raise 'Unsupported OS'
    end
  end
