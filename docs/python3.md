# Python 3

Given that python 2.7 will be EOL on December 31st, 2019, this project will
be transitioning to Python 3 in the short/mid-term future. Unfortunately the 
lack of widespread support for Python 3 in general on AIX makes it slightly
more challenging to set an aggressive timeline as we first need to enable a
stable environment and installation.

The following set of notes are development notes that should not be of much
particular interest to the common user.The notes described here have been
accounted for in the omnibus build. Regardless these also kept here for
reference purposes.

## Architecture

You may decide to build a 32 or 64 bit python, either is fine, but make sure
you are consistent in the way you build your dependencies such that all deps
are built to match the target architecture. GCC default to 32-bit builds.

To enable 64-bit builds, please us the `-maix64` CFLAG.

Note: in our experience the 32-bit build has been easier to build. 

## Requirements

Building a complete python 3 environment presents its challenges due to the 
high number of dependencies, some are optional, some are not, regardless, we 
want to build a complete environment so both mandatory and optional deps will
be targeted. These dependencies include:

- openssl (1.0.2p)
- readline (6.3)
- bzip2 (1.0.6)
- zlib (1.2.11)
- gdbm (1.13 or 1.18?)
- sqlite
- xz (5.2.4)
- ncurses (6.1)

## Building Dependencies

In most cases the dependencies are built with your usual autoconf workflow
(configure, make, make install). The GCC compiler will be used both for 
dependencies and python 3, so you will need that installed in your build
environment.

In an attempt to keep the build siloed from the rest of the system, builds
will target the `/opt/datadog` prefix. For each dependency, in general, you
should build as follows:

32-bit:
### Configure
```
CC="gcc -lgcc" CFLAGS="-I/opt/datadog/include -I/opt/freeware/include" LDFLAGS="-L/opt/datadog/lib -L/opt/freeware/lib" ./configure --prefix=/opt/datadog
```

### Make
```
make
make install
```

64-bit:
### Configure
```
OBJECT_MODE=64 CC="gcc -lgcc" CFLAGS="-maix64 -I/opt/datadog/include -I/opt/freeware/include" LDFLAGS="-L/opt/datadog/lib -L/opt/freeware/lib64 -L/opt/freeware/lib" ./configure --prefix=/opt/datadog
```

### Make
```
OBJECT_MODE=64 make
make install
```

Note: you may want to add memory management attributes such as the `-bmaxdata` 
flag. The following excerpt is from the python release notes. 
```
Note: this section may not apply when compiling Python as a 64 bits
application.

By default on AIX each program gets one segment register for its data

segment. As each segment register covers 256 MB, a Python program that
would use more than 256MB will raise a MemoryError.

To allocate more segment registers to Python, you must use the linker
option -bmaxdata to specify the number of bytes you need in the data
segment.

For example, if you want to allow 512MB of memory for Python, you
should build using:

make LINKFORSHARED="-Wl,-bE:Modules/python.exp -lld -Wl,-bmaxdata:0x20000000"

You can allow up to 2GB of memory for Python by using the value
0x80000000 for maxdata.

It is also possible to go beyond 2GB of memory by activating Large
Page Use. You should consult the IBM documentation if you need to use
this option. You can also follow more discussion concerning this
aspect in issue 11212.

http://publib.boulder.ibm.com/infocenter/aix/v6r1/index.jsp?topic=/com.ibm.aix.cmds/doc/aixcmds3/ldedit.htm
```

64-bit success: 
 - openssl
 - readline
 - sqlite 
 - zlib 


64-bit challenges: 
 - libgdbm: building static succeeds easily, 64bit cause issues while 
            linking w/ so during gdbmtool build phase
```
CC="gcc -lgcc" CFLAGS="-I/opt/datadog/include -I/opt/freeware/include" LDFLAGS="-L/opt/datadog/lib -L/opt/freeware/lib" ./configure --prefix=/opt/datadog --enable-libgdbm-compat --disable-shared
```
 - libxz: building static succeeds easily, 64bit cause issues while 
            linking w/ so
```
CC="gcc -lgcc" CFLAGS="-I/opt/datadog/include -I/opt/freeware/include" LDFLAGS="-L/opt/datadog/lib -L/opt/freeware/lib" ./configure --prefix=/opt/datadog --enable-libgdbm-compat --disable-shared
```
 - bzip2: requires patching the Makefile.
```
24c24
< CCFLAGS=$(CFLAGS) -Wall -Winline -O2 -g $(BIGFILES)
---
> CFLAGS=-Wall -Winline -O2 -g $(BIGFILES)
41c41
<       $(CC) $(CCFLAGS) $(LDFLAGS) -o bzip2 bzip2.o -L. -lbz2
---
>       $(CC) $(CFLAGS) $(LDFLAGS) -o bzip2 bzip2.o -L. -lbz2
44c44
<       $(CC) $(CCFLAGS) $(LDFLAGS) -o bzip2recover bzip2recover.o
---
>       $(CC) $(CFLAGS) $(LDFLAGS) -o bzip2recover bzip2recover.o
118c118
<       $(CC) $(CCFLAGS) -c blocksort.c
---
>       $(CC) $(CFLAGS) -c blocksort.c
120c120
<       $(CC) $(CCFLAGS) -c huffman.c
---
>       $(CC) $(CFLAGS) -c huffman.c
122c122
<       $(CC) $(CCFLAGS) -c crctable.c
---
>       $(CC) $(CFLAGS) -c crctable.c
124c124
<       $(CC) $(CCFLAGS) -c randtable.c
---
>       $(CC) $(CFLAGS) -c randtable.c
126c126
<       $(CC) $(CCFLAGS) -c compress.c
---
>       $(CC) $(CFLAGS) -c compress.c
128c128
<       $(CC) $(CCFLAGS) -c decompress.c
---
>       $(CC) $(CFLAGS) -c decompress.c
130c130
<       $(CC) $(CCFLAGS) -c bzlib.c
---
>       $(CC) $(CFLAGS) -c bzlib.c
132c132
<       $(CC) $(CCFLAGS) -c bzip2.c
---
>       $(CC) $(CFLAGS) -c bzip2.c
134c134
<       $(CC) $(CCFLAGS) -c bzip2recover.c
---
>       $(CC) $(CFLAGS) -c bzip2recover.c
```


There are some exceptions:

### OpenSSL

Requires perl5, shouldn't be a problem as it's bundled with AIX.

#### Configure
32-bit:
```
CC="gcc -lgcc" CFLAGS="-I/opt/datadog/include -I/opt/freeware/include" LDFLAGS="-L/opt/datadog/lib -L/opt/freeware/lib" ./Configure --prefix=/opt/datadog -maix32 aix-gcc
```

64-bit:
```
CC="gcc -lgcc" CFLAGS="-I/opt/datadog/include -I/opt/freeware/include" LDFLAGS="-L/opt/datadog/lib -L/opt/freeware/lib" ./Configure --prefix=/opt/datadog -maix64 aix64-gcc
```

### bzip2

#### Make
```
CC="gcc -lgcc" CFLAGS="-I/opt/datadog/include -I/opt/freeware/include" LDFLAGS="-L/opt/datadog/lib -L/opt/freeware/lib" make install PREFIX=/opt/datadog
```

### gdbm 

#### Configure
```
CC="gcc -lgcc" CFLAGS="-I/opt/datadog/include -I/opt/freeware/include -D_LARGE_FILES" LDFLAGS="-L/opt/datadog/lib -L/opt/freeware/lib" ./configure --enable-libgdbm-compat --prefix=/opt/datadog
```

#### Make
```
make
make install
```

Note: you might get some warnings during the link phase regarding duplicate symbols, these should be fine.
