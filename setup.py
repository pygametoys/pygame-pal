try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension

try:
    from Cython.Distutils import build_ext

    ext_modules=[
        Extension("pgpal._yj1",
                sources=["yj1backend/_yj1.pyx"],
        )
    ]
    ext_kwargs = dict(
        cmdclass={'build_ext': build_ext},
        ext_modules = ext_modules
    }
except ImportError:
    ext_kwargs = {}

setup(
    name="PyGame-Pal",
    description="A pygame-based open-source re-implemention of the classic Chinese RPG game 'Chinese Paladin'",
    license="GPLv3",
    install_requires=[
        'cython'
        'pygame',
        'attrs',
        'configobj',
        'six',
        'chardet',
        'pyaudio',
        'wrapt',
        'mido',
        'pyperclip',
        "enum34 ; python_version <= '2.7'",
        "textwrap3 ; python_version <= '2.7'",
        "backports.functools_lru_cache ; python_version <= '2.7'",
        "backports.functools_partialmethod ; python_version <= '2.7'"
    ],
    extras_require={
        'rix': ['pyopl'],
        'video': ['pyav >= 0.4.0'],
        'console': ['ptpython'],
        'speedup': ["psyco ; python_version < '2.7' and platform_machine == 'x86' and platform_python_implementation == 'CPython'"]
    },
    packages=['pgpal',
              'pgpal.configpage'],
    package_dir={'pgpal': 'pgpal',
                 'pgpal.configpage': 'pgpal/configpage'},
    scripts=['pygame-pal.py', 'pgpal-config.py'],
    **ext_kwargs
)
